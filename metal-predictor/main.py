from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from config import COLLECTION_NAME  # noqa: E402  (after load_dotenv)


# ---------------------------------------------------------------------------
# Startup lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts (and again on every restart).

    Decision tree
    ─────────────
    Collection missing  →  full ingest (first launch or manual wipe)
    Collection exists   →  incremental ingest (append only new trading days)
                           then load the vectorstore and build the RAG chain

    This means every restart automatically picks up any new daily data that
    arrived since the last run — no manual trigger needed.
    """
    print("=" * 60)
    print("  Metal Price Prediction API — starting up")
    print("=" * 60)

    app.state.rag_chain = None

    try:
        from embeddings.embedder import get_embedder
        from processing.chunker import chunk_all_metals
        from rag.pipeline import build_rag_chain
        from vectorstore.qdrant_store import (
            _get_client,
            append_chunks,
            collection_exists,
            get_latest_ingested_dates,
            get_retriever,
            init_vectorstore,
            load_vectorstore,
        )

        embedder = get_embedder()

        probe = _get_client()
        has_collection = collection_exists(probe)

        if not has_collection:
            # ── First launch: full ingest ────────────────────────────────
            print("  No existing collection — running full ingest …")
            from data.data_collector import fetch_all_metals

            metal_data = fetch_all_metals()
            if not metal_data:
                raise RuntimeError("Could not fetch any metal data during startup.")

            chunks = chunk_all_metals(metal_data)
            if not chunks:
                raise RuntimeError("No chunks produced during startup ingestion.")

            vectorstore = init_vectorstore(chunks, embedder)
            print(f"  Full ingest complete — {len(chunks)} chunks stored.")

        else:
            # ── Subsequent restarts: incremental ingest ──────────────────
            print("  Existing collection found — checking for new data …")
            latest_dates = get_latest_ingested_dates(probe)

            from data.data_collector import fetch_all_metals

            metal_data = fetch_all_metals(since_dates=latest_dates)

            if metal_data:
                all_new_chunks = chunk_all_metals(metal_data)

                # Drop chunks already stored (overlap window artefacts)
                new_chunks = [
                    c for c in all_new_chunks
                    if c["metadata"]["end_date"] > (
                        latest_dates.get(c["metadata"]["metal"], "")
                    )
                ]

                if new_chunks:
                    append_chunks(new_chunks, embedder)
                    print(f"  Incremental update — {len(new_chunks)} new chunks appended.")
                else:
                    print("  Collection already up to date — nothing new to add.")
            else:
                print("  No new data fetched — collection is current.")

            vectorstore = load_vectorstore(embedder)

        probe.close()

        retriever = get_retriever(vectorstore, lookback_years=2)
        app.state.rag_chain = build_rag_chain(retriever)
        print("  RAG pipeline ready.")

    except Exception as exc:
        print(f"  WARNING: RAG pipeline could not be initialised: {exc}")
        print("  POST /ingest to initialise the pipeline manually.")

    print("=" * 60)

    yield

    print("Metal Price Prediction API — shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Metal Price Prediction API",
    description=(
        "RAG-based sell/hold prediction for Copper, Zinc, and Aluminum "
        "using historical Yahoo Finance data and Qdrant vector search."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

from api.routes import router  # noqa: E402

app.include_router(router)

# Serve built React frontend (dashboard/ is produced by `npm run build` in frontend/)
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

if os.path.exists("dashboard") and os.path.isdir("dashboard"):
    if os.path.exists("dashboard/assets"):
        app.mount("/assets", StaticFiles(directory="dashboard/assets"), name="assets")

    @app.get("/", response_class=FileResponse)
    async def serve_dashboard():
        return FileResponse("dashboard/index.html")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
