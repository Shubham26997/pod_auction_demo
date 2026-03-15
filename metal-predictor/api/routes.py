import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from config import METALS, METALS_TO_MT_FACTOR, UNIT_LABELS, VALID_UNITS

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class PredictRequest(BaseModel):
    metal: str = Field(..., description="Metal name: copper, zinc, or aluminum")
    current_price: float = Field(
        ..., gt=0,
        description=(
            "Market price per unit in the currency/unit matching 'unit' below. "
            "For LME prices (the default), enter the USD/MT spot price."
        ),
    )
    quantity: float = Field(..., gt=0, description="How much metal you hold")
    unit: str = Field(
        default="metric_ton",
        description=(
            "Unit for both quantity and current_price. "
            "LME standard is metric_ton (USD/MT). "
            "Options: metric_ton | kg | pound | lot"
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health", summary="Health check")
async def health_check():
    """Returns service health status."""
    return {"status": "healthy", "service": "metal-predictor"}


@router.get("/metals", summary="List supported metals")
async def list_metals():
    """Returns all metals supported by the prediction system and their tickers."""
    return {
        "metals": list(METALS.keys()),
        "tickers": METALS,
    }


@router.post("/predict", summary="Predict sell/hold decision")
async def predict_metal(request_data: PredictRequest, request: Request):
    """
    Given a metal, its current price, and the quantity held, returns an AI-driven
    trading recommendation (SELL NOW / WAIT / LOSS WARNING) backed by historical
    RAG context from Qdrant.

    All historical data stored in Qdrant follows **LME (London Metal Exchange)**
    pricing conventions — prices are normalised to **USD per metric ton (USD/MT)**.
    For best results, pass `current_price` as the LME USD/MT spot price and leave
    `unit` as the default `metric_ton`.
    """
    metal = request_data.metal.lower().strip()
    unit = request_data.unit.lower().strip()

    if metal not in METALS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported metal '{metal}'. Supported: {list(METALS.keys())}",
        )

    if unit not in VALID_UNITS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported unit '{unit}'. Supported: {sorted(VALID_UNITS)}",
        )

    chain = getattr(request.app.state, "rag_chain", None)
    if chain is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "RAG pipeline is not initialised. "
                "POST /ingest to trigger data ingestion, or restart the service."
            ),
        )

    from rag.pipeline import predict

    try:
        result = predict(
            chain,
            metal,
            request_data.current_price,
            request_data.quantity,
            unit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc

    unit_label = UNIT_LABELS[unit]
    return {
        "metal": metal,
        "quantity": request_data.quantity,
        "unit": unit_label,
        "current_price": request_data.current_price,
        "price_per": f"USD per {unit_label}",
        "total_value_usd": round(request_data.current_price * request_data.quantity, 2),
        "analysis": result["prediction"],
        "context_used": result["source_documents"],
    }


class IngestRequest(BaseModel):
    mode: str = Field(
        default="incremental",
        description=(
            "'incremental' (default) — append only new trading days since last run. "
            "'full' — wipe the collection and rebuild from scratch."
        ),
    )


@router.post("/ingest", summary="Trigger data ingestion")
async def trigger_ingest(body: IngestRequest, request: Request):
    """
    Manually trigger the ingestion pipeline.

    - **incremental** (default): fetches only new trading days and appends them.
      Safe to call on a schedule; does nothing if already up to date.
    - **full**: deletes and rebuilds the entire collection from scratch.
      Use after changing DATA_PERIOD / DATA_START_DATE or to fix corrupt data.
    """
    if body.mode not in ("incremental", "full"):
        raise HTTPException(
            status_code=400,
            detail="mode must be 'incremental' or 'full'",
        )

    try:
        from data.data_collector import fetch_all_metals
        from embeddings.embedder import get_embedder
        from processing.chunker import chunk_all_metals
        from rag.pipeline import build_rag_chain
        from vectorstore.qdrant_store import (
            append_chunks,
            collection_exists,
            get_latest_ingested_dates,
            get_retriever,
            init_vectorstore,
            load_vectorstore,
        )

        embedder = get_embedder()
        chunks_added = 0

        if body.mode == "full":
            print("[/ingest] Full reset …")
            metal_data = fetch_all_metals()
            if not metal_data:
                raise ValueError("No metal data fetched.")
            chunks = chunk_all_metals(metal_data)
            if not chunks:
                raise ValueError("No chunks produced.")
            vectorstore = init_vectorstore(chunks, embedder)
            chunks_added = len(chunks)
            metals_processed = list(metal_data.keys())

        else:  # incremental
            print("[/ingest] Incremental update …")

            if not collection_exists():
                # No collection yet → fall back to full
                metal_data = fetch_all_metals()
                if not metal_data:
                    raise ValueError("No metal data fetched.")
                chunks = chunk_all_metals(metal_data)
                if not chunks:
                    raise ValueError("No chunks produced.")
                vectorstore = init_vectorstore(chunks, embedder)
                chunks_added = len(chunks)
                metals_processed = list(metal_data.keys())
            else:
                latest_dates = get_latest_ingested_dates()
                metal_data = fetch_all_metals(since_dates=latest_dates)
                metals_processed = list(metal_data.keys())

                if metal_data:
                    all_new = chunk_all_metals(metal_data)
                    new_chunks = [
                        c for c in all_new
                        if c["metadata"]["end_date"] > (
                            latest_dates.get(c["metadata"]["metal"], "")
                        )
                    ]
                    if new_chunks:
                        append_chunks(new_chunks, embedder)
                        chunks_added = len(new_chunks)

                vectorstore = load_vectorstore(embedder)

        # Rebuild the live RAG chain with the updated vectorstore
        retriever = get_retriever(vectorstore, lookback_years=2)
        request.app.state.rag_chain = build_rag_chain(retriever)

        print(f"[/ingest] Done — {chunks_added} chunks added/updated.")

        return {
            "status": "success",
            "mode": body.mode,
            "metals_processed": metals_processed,
            "chunks_added": chunks_added,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message (metal trading question)")
    session_id: str | None = Field(
        default=None,
        description=(
            "Session ID returned from a previous /chat call. "
            "Omit (or pass null) to start a new conversation."
        ),
    )


@router.post("/chat", summary="Chat with the metal trading assistant")
async def chat_endpoint(body: ChatRequest, request: Request):
    """
    Send a message to the LME metal trading assistant and receive a reply.

    The assistant can:
    - Answer general questions about LME base metals (copper, zinc, aluminum).
    - Fetch the latest LME spot price for a metal.
    - Provide a SELL NOW / WAIT / LOSS WARNING recommendation when the user
      supplies a metal, their current price, and the quantity they hold.

    **Conversation memory**: supply the ``session_id`` returned by the previous
    call to maintain context across multiple turns.  Omit it (or pass ``null``)
    to start a fresh session — a new ``session_id`` is created and returned.

    **LME pricing**: all prices are in USD per metric ton (USD/MT).  When asking
    for a prediction, enter the current LME spot price in USD/MT.

    Example questions:
    - "What is the current LME copper price?"
    - "I hold 50 metric tons of zinc at 2800 USD/MT. Should I sell?"
    - "What was the trend for aluminum last month?"
    """
    from chat.agent import chat

    try:
        result = chat(
            user_message=body.message,
            rag_chain=getattr(request.app.state, "rag_chain", None),
            session_id=body.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}") from exc

    return {
        "session_id": result["session_id"],
        "reply": result["reply"],
        "tool_calls_made": result["tool_calls_made"],
    }


@router.get("/chat/{session_id}/history", summary="Get conversation history")
async def get_chat_history(session_id: str):
    """
    Retrieve the full conversation history for a session.

    Returns only user and assistant text turns (internal tool messages are
    filtered out).  Returns an empty list if the session does not exist.
    """
    from chat.agent import get_history

    return {
        "session_id": session_id,
        "history": get_history(session_id),
    }


@router.delete("/chat/{session_id}", summary="Clear conversation history")
async def clear_chat_session(session_id: str):
    """
    Delete all stored conversation history for the given session ID.

    Use this to reset context when starting a new topic or when the user
    explicitly asks to forget previous messages.  The same session_id can
    be reused after clearing — it will behave like a new session.
    """
    from chat.agent import clear_session

    found = clear_session(session_id)
    if not found:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )
    return {"status": "cleared", "session_id": session_id}


# ---------------------------------------------------------------------------
# Prices API (with Redis cache → Qdrant fallback)
# ---------------------------------------------------------------------------

# Bump this when the shape or unit of cached data changes (e.g. USD/lb → USD/MT
# conversion added).  Old keys are never matched and expire naturally via TTL.
_CACHE_VERSION = "v2"

_RANGE_DAYS: dict[str, int | None] = {
    "1d": 1, "1y": 365, "2y": 730, "5y": 1825, "all": None,
}
_RANGE_TTL: dict[str, int] = {
    "1d": 3600, "1y": 86400, "2y": 86400, "5y": 86400, "all": 86400,
}


@router.get("/api/prices", summary="Current LME prices for all metals")
async def get_prices():
    """
    Returns the latest LME close price, unit, date, and weekly change% for
    each metal.  Served from Redis (TTL 24 h); falls back to Qdrant on miss.
    """
    from cache.redis_client import cache_get, cache_set
    from config import COLLECTION_NAME
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue
    from vectorstore.qdrant_store import _get_client, collection_exists

    cached = cache_get(f"{_CACHE_VERSION}:prices:all")
    if cached:
        return cached

    client = _get_client()
    try:
        if not collection_exists(client):
            return {m: {"price": 0.0, "unit": "USD/MT", "as_of": "", "change_pct": 0.0} for m in METALS}

        result: dict = {}
        for metal_name in METALS:
            points, _ = client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=Filter(must=[
                    FieldCondition(key="metadata.metal", match=MatchValue(value=metal_name))
                ]),
                limit=100_000,
                with_payload=True,
                with_vectors=False,
            )

            metas = sorted(
                [p.payload.get("metadata", {}) for p in points if p.payload],
                key=lambda m: m.get("end_timestamp", 0),
            )
            if not metas:
                continue

            latest = metas[-1]
            # Apply USD/lb → USD/MT conversion for metals whose Yahoo data is
            # stored in USD/lb (copper/HG=F), unless already converted at ingest
            # time (indicated by price_unit == "USD/MT" in the chunk metadata).
            already_converted = latest.get("price_unit") == "USD/MT"
            factor = 1.0 if already_converted else METALS_TO_MT_FACTOR.get(metal_name, 1.0)
            result[metal_name] = {
                "price": round(float(latest.get("close", 0)) * factor, 2),
                "unit": "USD/MT",
                "as_of": latest.get("end_date", ""),
                "change_pct": round(float(latest.get("pct_change", 0)), 2),
            }

        cache_set(f"{_CACHE_VERSION}:prices:all", result, ttl=86400)
        return result
    finally:
        client.close()


@router.get("/api/chart/{metal}", summary="OHLCV time-series for chart rendering")
async def get_chart(metal: str, range: str = "5y"):
    """
    Returns OHLCV data for a metal over the requested range.
    range: 1d | 1y | 2y | 5y | all
    Served from Redis; falls back to Qdrant on miss.
    """
    from cache.redis_client import cache_get, cache_set
    from config import COLLECTION_NAME
    from qdrant_client.http.models import FieldCondition, Filter, MatchValue, Range
    from vectorstore.qdrant_store import _get_client, collection_exists

    metal = metal.lower().strip()
    if metal not in METALS:
        raise HTTPException(status_code=400, detail=f"Unknown metal. Supported: {list(METALS.keys())}")

    range_key = range.lower()
    if range_key not in _RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Unknown range. Supported: {list(_RANGE_DAYS.keys())}")

    cache_key = f"{_CACHE_VERSION}:chart:{metal}:{range_key}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    client = _get_client()
    try:
        if not collection_exists(client):
            return {"metal": metal, "range": range_key, "unit": "USD/MT", "available_from": "", "data": []}

        must = [FieldCondition(key="metadata.metal", match=MatchValue(value=metal))]
        days = _RANGE_DAYS[range_key]
        if days is not None:
            cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp()
            must.append(FieldCondition(key="metadata.end_timestamp", range=Range(gte=cutoff)))

        points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(must=must),
            limit=100_000,
            with_payload=True,
            with_vectors=False,
        )

        metas = sorted(
            [p.payload.get("metadata", {}) for p in points if p.payload],
            key=lambda m: m.get("end_date", ""),
        )

        data = []
        for m in metas:
            if not m.get("end_date"):
                continue
            already_converted = m.get("price_unit") == "USD/MT"
            factor = 1.0 if already_converted else METALS_TO_MT_FACTOR.get(metal, 1.0)
            data.append({
                "date": m.get("end_date", ""),
                "open":  round(float(m.get("open",  0)) * factor, 2),
                "high":  round(float(m.get("high",  0)) * factor, 2),
                "low":   round(float(m.get("low",   0)) * factor, 2),
                "close": round(float(m.get("close", 0)) * factor, 2),
                "volume": int(float(m.get("avg_volume", 0))),
                "change_pct": round(float(m.get("pct_change", 0)), 2),
            })

        response = {
            "metal": metal,
            "range": range_key,
            "unit": "USD/MT",
            "available_from": data[0]["date"] if data else "",
            "data": data,
        }

        cache_set(cache_key, response, ttl=_RANGE_TTL[range_key])
        return response
    finally:
        client.close()


@router.delete("/api/cache", summary="Clear all cached prices and chart data")
async def clear_cache():
    """Deletes all Redis keys with prefix 'prices:' or 'chart:'."""
    from cache.redis_client import cache_delete_pattern
    cleared = cache_delete_pattern(f"{_CACHE_VERSION}:prices:*") + cache_delete_pattern(f"{_CACHE_VERSION}:chart:*")
    return {"status": "ok", "keys_cleared": cleared}


@router.get("/api/cache/status", summary="Show all cached keys and their TTLs")
async def get_cache_status():
    """Returns all active cache keys with remaining TTL in seconds."""
    from cache.redis_client import cache_status
    return {"keys": cache_status()}
