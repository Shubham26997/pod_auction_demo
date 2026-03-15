from langchain_openai import OpenAIEmbeddings

from config import EMBEDDING_MODEL


def get_embedder() -> OpenAIEmbeddings:
    """
    Initialise and return a LangChain OpenAIEmbeddings instance configured
    to use the text-embedding-3-small model.  The OpenAI API key is picked up
    automatically from the OPENAI_API_KEY environment variable.
    """
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)
