import os
from typing import Any

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from config import COLLECTION_NAME, EMBEDDING_DIMENSION, QDRANT_HOST, QDRANT_PATH, QDRANT_PORT


def _get_client() -> QdrantClient:
    """
    Return a QdrantClient in the appropriate mode:

    - Server mode  (QDRANT_HOST is set): connects to a running Qdrant container.
      Used inside Docker — gives access to the Qdrant REST API and dashboard
      at http://localhost:6333/dashboard.

    - Embedded mode (QDRANT_HOST is empty): stores data in a local directory.
      Used for local development without Docker; no dashboard available.
    """
    if QDRANT_HOST:
        return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    os.makedirs(QDRANT_PATH, exist_ok=True)
    return QdrantClient(path=QDRANT_PATH)


# ---------------------------------------------------------------------------
# Inspect existing data
# ---------------------------------------------------------------------------

def collection_exists(client: QdrantClient | None = None) -> bool:
    """Return True if the metal_prices collection is already on disk."""
    c = client or _get_client()
    return COLLECTION_NAME in {col.name for col in c.get_collections().collections}


def get_latest_ingested_dates(client: QdrantClient | None = None) -> dict[str, str]:
    """
    Scroll through all stored points and return the most recent end_date
    for each metal.

    Returns {metal_name: "YYYY-MM-DD"}.
    An empty dict means the collection is empty or does not exist.
    """
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue
    from config import METALS

    c = client or _get_client()
    if not collection_exists(c):
        return {}

    latest: dict[str, str] = {}

    for metal_name in METALS:
        # Scroll all points for this metal (vectors not needed)
        points, _ = c.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.metal",
                        match=MatchValue(value=metal_name),
                    )
                ]
            ),
            limit=100_000,
            with_payload=True,
            with_vectors=False,
        )

        dates = [
            p.payload.get("metadata", {}).get("end_date")
            for p in points
            if p.payload
        ]
        dates = [d for d in dates if d]

        if dates:
            latest[metal_name] = max(dates)

    return latest


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def init_vectorstore(
    chunks: list[dict[str, Any]],
    embedder: OpenAIEmbeddings,
) -> QdrantVectorStore:
    """
    Create a BRAND-NEW collection from scratch (full ingest / reset).

    Deletes any existing collection with the same name first so the
    operation is idempotent.  Use append_chunks() for incremental updates.
    """
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    client = _get_client()

    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Deleted existing collection '{COLLECTION_NAME}' for full reset")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=Distance.COSINE),
    )

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embedder,
    )
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    return vectorstore


def append_chunks(
    chunks: list[dict[str, Any]],
    embedder: OpenAIEmbeddings,
) -> QdrantVectorStore:
    """
    Append new chunks to an EXISTING collection without touching old data.

    The collection must already exist (call init_vectorstore first if not).
    This is the function used for all daily / incremental updates.
    """
    if not chunks:
        raise ValueError("append_chunks called with an empty chunk list")

    texts = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    client = _get_client()
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embedder,
    )
    vectorstore.add_texts(texts=texts, metadatas=metadatas)
    return vectorstore


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def load_vectorstore(embedder: OpenAIEmbeddings) -> QdrantVectorStore:
    """Load an existing collection from disk (no data changes)."""
    client = _get_client()
    if not collection_exists(client):
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' not found in '{QDRANT_PATH}'. "
            "Run ingestion first."
        )
    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embedder,
    )


def get_retriever(
    vectorstore: QdrantVectorStore,
    metal_filter: str | None = None,
    k: int = 5,
    lookback_years: int = 2,
):
    """
    Return a LangChain retriever with two pre-filters applied at Qdrant level:

    1. Date-range filter  — only chunks whose end_timestamp (Unix float stored
       in metadata) is >= (today - lookback_years).  Defaults to 2 years so
       predictions are driven by recent price patterns rather than decade-old data.
       Increase lookback_years when you want the LLM to consider older history.

    2. Metal filter (optional) — restrict to a single metal's chunks.

    Both filters are merged into one Qdrant Filter(must=[...]) to avoid
    multiple round-trips.
    """
    from datetime import datetime, timedelta, timezone

    from qdrant_client.http.models import FieldCondition, Filter, MatchValue, Range

    must_conditions = []

    # -- Date-range pre-filter -----------------------------------------------
    cutoff_ts = (
        datetime.now(tz=timezone.utc) - timedelta(days=365 * lookback_years)
    ).timestamp()
    must_conditions.append(
        FieldCondition(
            key="metadata.end_timestamp",
            range=Range(gte=cutoff_ts),
        )
    )

    # -- Metal filter (optional) ---------------------------------------------
    if metal_filter:
        must_conditions.append(
            FieldCondition(
                key="metadata.metal",
                match=MatchValue(value=metal_filter),
            )
        )

    search_kwargs: dict[str, Any] = {
        "k": k,
        "filter": Filter(must=must_conditions),
    }

    return vectorstore.as_retriever(search_kwargs=search_kwargs)
