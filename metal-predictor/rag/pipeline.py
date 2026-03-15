from langchain_classic.chains import RetrievalQA
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import LLMChainExtractor
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from config import LLM_MODEL

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

TRADING_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are an expert commodity trading analyst specialising in base metals \
(copper, zinc, aluminum). Your role is to analyse historical price patterns and advise \
traders on the optimal timing for selling their metal inventory.

All historical prices in the data below are quoted in USD per metric ton (USD/MT), \
following LME (London Metal Exchange) standard conventions.  The trader's current \
position price is also expressed in USD/MT so the figures are directly comparable.

Use ONLY the historical data provided below to support your reasoning.

--- HISTORICAL DATA ---
{context}
--- END OF DATA ---

Trading Question:
{question}

Respond in EXACTLY this structured format (use the bold headers as shown):

**Decision:** [SELL NOW / WAIT / LOSS WARNING]
**Confidence:** [High / Medium / Low]
**Reasoning:** Provide 2-3 sentences citing specific patterns, trends, or volatility \
figures from the retrieved data that support your decision.  Reference prices in USD/MT.
**Suggested Action:** Give a concrete, actionable recommendation (e.g. sell all / sell \
50 %% and hold the rest / wait for next week's data).

Be concise, data-driven, and avoid speculation beyond the provided context.""",
)


# ---------------------------------------------------------------------------
# Contextual compression
# ---------------------------------------------------------------------------


def build_compressed_retriever(
    base_retriever,
    llm: ChatOpenAI,
) -> ContextualCompressionRetriever:
    """
    Wrap a base retriever with LangChain ContextualCompressionRetriever.

    LLMChainExtractor uses the LLM to strip sentences from each retrieved
    chunk that are irrelevant to the query before they are passed to the
    final RetrievalQA chain.  This reduces prompt token usage and keeps the
    context window focused on price/trend signals that actually matter.
    """
    compressor = LLMChainExtractor.from_llm(llm)
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )


# ---------------------------------------------------------------------------
# Chain builder
# ---------------------------------------------------------------------------


def build_rag_chain(retriever) -> RetrievalQA:
    """
    Construct a LangChain RetrievalQA chain:
    1. The base retriever fetches top-k chunks from Qdrant (already pre-filtered
        by date range and optionally by metal).
    2. LLMChainExtractor compresses each chunk — removing sentences irrelevant
        to the query — before they reach the final prompt.
    3. gpt-4o-mini reasons over the compressed context with the trading prompt.
    """
    llm = ChatOpenAI(model=LLM_MODEL, temperature=0.1)

    # Wrap base retriever with contextual compression to reduce token waste
    compressed_retriever = build_compressed_retriever(retriever, llm)

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=compressed_retriever,
        chain_type_kwargs={"prompt": TRADING_PROMPT},
        return_source_documents=True,
    )

    return chain


# ---------------------------------------------------------------------------
# Prediction helper
# ---------------------------------------------------------------------------


def predict(
    chain: RetrievalQA,
    metal: str,
    current_price: float,
    quantity: float,
    unit: str = "metric_ton",
) -> dict:
    """
    Format a trading query and run it through the RAG chain.

    unit    : explicit measurement unit so the LLM knows the scale of the position.
            One of: metric_ton | kg | pound | lot

    Returns a dict with:
    - 'prediction': the LLM's textual analysis
    - 'source_documents': list of (compressed) chunk strings used as context
    """
    # Map internal unit key to a human-readable phrase the LLM can reason about
    unit_phrases = {
        "metric_ton": "metric ton(s)",
        "kg":         "kilogram(s)",
        "pound":      "pound(s)",
        "lot":        "exchange lot(s)",
    }
    unit_phrase = unit_phrases.get(unit, f"{unit}(s)")

    # For metric_ton (the LME default) we can state the price directly as
    # "USD/MT" so it aligns with the LME-normalised historical data in Qdrant.
    if unit == "metric_ton":
        price_clause = f"The current LME spot price is {current_price:,.2f} USD/MT."
    else:
        price_clause = (
            f"The current market price is {current_price:,.4f} USD per {unit_phrase}."
        )

    query = (
        f"I hold {quantity:,.2f} {unit_phrase} of {metal.capitalize()} "
        f"(LME base metal). "
        f"{price_clause} "
        f"Total position value: {current_price * quantity:,.2f} USD. "
        f"Based on historical LME price patterns, weekly trends, volatility, and "
        f"traded volume for {metal}, should I SELL NOW, WAIT for a better price, "
        f"or is this a LOSS WARNING situation?"
    )

    result = chain.invoke({"query": query})

    return {
        "prediction": result.get("result", ""),
        "source_documents": [
            doc.page_content for doc in result.get("source_documents", [])
        ],
    }
