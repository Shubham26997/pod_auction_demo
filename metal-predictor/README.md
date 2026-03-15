# Metal Price Prediction System

A RAG-based prediction system for **Copper**, **Zinc**, and **Aluminum** that retrieves
historical weekly price patterns from a Qdrant vector store and asks GPT-4o-mini whether
the current price is a good time to sell.

## Architecture

```
Yahoo Finance → yfinance → weekly chunks → OpenAI embeddings
                                                ↓
                                     Qdrant (local / file mode)
                                                ↓
FastAPI  ←  LangChain RetrievalQA  ←  similarity search  ←  /predict
```

## Tech Stack

| Layer | Tool |
|---|---|
| Data collection | `yfinance` |
| Preprocessing | `pandas`, `numpy` |
| Embeddings | `langchain-openai` / `text-embedding-3-small` |
| Vector DB | `qdrant-client` (local mode) + `langchain-qdrant` |
| LLM | `gpt-4o-mini` via `langchain-openai` |
| API | `FastAPI` + `uvicorn` |
| Package manager | `uv` |
| Containerisation | Docker + Docker Compose |

---

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) installed

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and enter the project

```bash
git clone <repo-url>
cd metal-predictor
```

### 3. Install dependencies

```bash
uv sync
```

### 4. Configure environment

```bash
cp .env.example .env
# Open .env and add your real OpenAI API key
```

### 5. Run data ingestion (one-time setup)

```bash
uv run python scripts/ingest.py
```

This fetches 5 years of OHLCV data for copper, zinc, and aluminum; chunks it into
overlapping 7-day windows; embeds each chunk; and stores ~2 000+ vectors in
`./qdrant_storage/`.

### 6. Start the development server

```bash
uv run uvicorn main:app --reload
```

API is available at `http://localhost:8000`.
Interactive docs at `http://localhost:8000/docs`.

---

## Docker (Production)

### Build and start

```bash
# Copy env file first
cp .env.example .env
# Add your OPENAI_API_KEY to .env

docker-compose up --build
```

On first launch the container automatically runs the ingestion pipeline.
Qdrant data is persisted in the `qdrant_data` Docker volume — subsequent
restarts skip ingestion and load from disk directly.

### Stop

```bash
docker-compose down
```

The `qdrant_data` volume is **not** removed by `docker-compose down`.
Use `docker-compose down -v` only if you intentionally want to wipe the data.

---

## API Reference

### `GET /health`

Returns service status.

```json
{"status": "healthy", "service": "metal-predictor"}
```

### `GET /metals`

Lists supported metals and their tickers.

```json
{
  "metals": ["copper", "zinc", "aluminum"],
  "tickers": {"copper": "HG=F", "zinc": "ZNC=F", "aluminum": "ALI=F"}
}
```

### `POST /predict`

Predict whether to sell at the current price.

All historical data is stored in **USD/MT (LME standard)**. Pass `current_price`
as the LME USD/MT spot price and leave `unit` as `metric_ton` (default).

**Request body:**

```json
{
  "metal": "copper",
  "current_price": 9450.00,
  "quantity": 25,
  "unit": "metric_ton"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `metal` | string | yes | `copper`, `zinc`, or `aluminum` |
| `current_price` | float | yes | Spot price in the unit chosen below |
| `quantity` | float | yes | How much metal you hold |
| `unit` | string | no | `metric_ton` (default / LME) \| `kg` \| `pound` \| `lot` |

**Response:**

```json
{
  "metal": "copper",
  "quantity": 25.0,
  "unit": "metric ton",
  "current_price": 9450.0,
  "price_per": "USD per metric ton",
  "total_value_usd": 236250.0,
  "analysis": "**Decision:** SELL NOW\n**Confidence:** High\n...",
  "context_used": ["Metal: copper | Week: 2024-01-08 to 2024-01-14 | Open: 9320.50 USD/MT | ..."]
}
```

### `POST /ingest`

Manually (re-)run the full ingestion pipeline.

```json
{
  "status": "success",
  "metals_processed": ["copper", "zinc", "aluminum"],
  "chunks_ingested": 2184
}
```

---

## Chat Feature

The `/chat` endpoint provides a conversational interface to the prediction system.
The assistant remembers conversation history within a session and can autonomously
call internal tools to answer your questions.

### What the assistant can do

| Capability | How to trigger |
|---|---|
| Fetch current LME price | "What is the current copper price?" |
| Predict sell/hold/wait | Provide metal + price + quantity in any message |
| Answer general LME questions | Ask freely — it redirects off-topic queries |
| Continue a conversation | Pass `session_id` from the previous response |

### Endpoints

#### `POST /chat`

```json
{
  "message": "I hold 50 metric tons of zinc at 2800 USD/MT. Should I sell?",
  "session_id": null
}
```

`session_id` is optional.  Omit it (or pass `null`) for a new session.  Reuse
the returned `session_id` in subsequent calls to maintain context.

**Response:**

```json
{
  "session_id": "3f2e1a9b-...",
  "reply": "**Decision:** WAIT\n**Confidence:** Medium\n...",
  "tool_calls_made": ["get_current_lme_price", "predict_sell_decision"]
}
```

`tool_calls_made` shows which internal tools the LLM invoked this turn (useful
for debugging; can be ignored in production).

#### `GET /chat/{session_id}/history`

Returns the full human-readable conversation history:

```json
{
  "session_id": "3f2e1a9b-...",
  "history": [
    {"role": "user",      "content": "What is the current copper price?"},
    {"role": "assistant", "content": "Copper — latest available price: 9 450.20 USD/MT ..."},
    {"role": "user",      "content": "I hold 25 MT at that price, should I sell?"},
    {"role": "assistant", "content": "**Decision:** SELL NOW ..."}
  ]
}
```

#### `DELETE /chat/{session_id}`

Clears the session history.  The same `session_id` can be reused afterwards
and will behave like a new session.

### Example multi-turn session

```bash
# Turn 1 — ask for current price
SESSION=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current LME copper price?"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# Turn 2 — follow up with a prediction (reuse session)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"I hold 25 metric tons at that price, should I sell?\", \"session_id\": \"$SESSION\"}"

# View full history
curl http://localhost:8000/chat/$SESSION/history

# Clear session
curl -X DELETE http://localhost:8000/chat/$SESSION
```

### Session storage

Sessions are stored **in-memory** in the running process.  They are lost on
server restart.  For persistent sessions across restarts, extend
`chat/agent.py` to use Redis or a database as the backing store.

---

## LME Pricing Standard

### What is LME?

The **London Metal Exchange (LME)** is the world reference market for industrial
metals.  All LME contracts — including copper, zinc, and aluminum — are quoted in
**USD per metric ton (USD/MT)**.

This system normalises every stored price to USD/MT so that:

1. Prices across all three metals are on the **same scale** (no apples-to-oranges
   comparisons between USD/lb copper and USD/MT zinc).
2. Traders can enter the **LME spot price directly** from any market data feed.
3. The LLM reasoning prompt explicitly anchors the analysis to USD/MT, preventing
   unit confusion in the generated advice.

### Yahoo Finance ticker units vs LME

Yahoo Finance doesn't always quote in LME units.  The table below shows which
tickers need conversion and what the system does automatically at ingest time:

| Metal | Yahoo Ticker | Yahoo Unit | LME Unit | Conversion applied |
|---|---|---|---|---|
| Copper | `HG=F` | USD/lb | USD/MT | × 2 204.6226 (1 MT = 2 204.6226 lbs) |
| Zinc | `ZNC=F` | USD/MT | USD/MT | none (already LME-aligned) |
| Aluminum | `ALI=F` | USD/MT | USD/MT | none (already LME-aligned) |

> **Note:** The conversion is applied to `Open`, `High`, `Low`, and `Close` columns
> only.  `pct_change`, `volatility`, and `avg_volume` are dimensionless ratios /
> counts and are unaffected.

### Using /predict with LME prices

Use `metric_ton` (the default unit) and enter the current LME spot price:

```bash
# Copper at ~9 450 USD/MT, holding 25 metric tons
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "metal": "copper",
       "current_price": 9450.00,
       "quantity": 25,
       "unit": "metric_ton"
     }'
```

You can also use other units if your quote source differs — just make sure
`current_price` matches the unit you select:

```bash
# Same position expressed in pounds (COMEX style: ~4.28 USD/lb)
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "metal": "copper",
       "current_price": 4.28,
       "quantity": 55115,
       "unit": "pound"
     }'
```

### Migration: full re-ingest required

If you have an existing Qdrant collection from before this change, the stored
copper prices are in **USD/lb** (~4.25) instead of **USD/MT** (~9 350).  Run a
full reset to rebuild with the correct units:

```bash
# Via CLI script
uv run python scripts/ingest.py --full

# Or via API
curl -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{"mode": "full"}'
```

---

## Scheduled Daily Ingestion

Keep the vector DB growing automatically without any manual steps.

### Run the scheduler

```bash
uv run python scripts/schedule_ingest.py
```

The process blocks and runs an incremental ingest every day at **00:05 UTC**.
It logs each run to stdout and tolerates failures gracefully (a bad run is
logged but the scheduler keeps running).

### Run as a background process

```bash
# Simple background with nohup
nohup uv run python scripts/schedule_ingest.py > logs/scheduler.log 2>&1 &

# Or with screen
screen -S metal-scheduler
uv run python scripts/schedule_ingest.py
# Ctrl+A, D  to detach
```

### Manual incremental update (one-shot)

```bash
uv run python scripts/ingest.py              # incremental (default)
uv run python scripts/ingest.py --full       # full reset
```

> **Note:** After upgrading from a version that did not store `end_timestamp`
> in chunk metadata, run `uv run python scripts/ingest.py --full` once so all
> vectors have the new field and date-range pre-filtering works correctly.

---

## Testing the full flow

```bash
# Health check
curl http://localhost:8000/health

# Predict (LME copper price in USD/MT)
curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{"metal": "copper", "current_price": 9450.00, "quantity": 25, "unit": "metric_ton"}'

# Re-ingest (if needed)
curl -X POST http://localhost:8000/ingest
```

---

## Data persistence test

```bash
# Start
docker-compose up -d

# Wait for ingestion to finish, then stop
docker-compose down

# Restart — should load from volume, NOT re-ingest
docker-compose up
```

You should see `Found existing collection 'metal_prices' — loading …` in the logs.

---

## Configuration

All constants live in `config.py`:

| Constant | Default | Description |
|---|---|---|
| `METALS` | copper/zinc/aluminum | Ticker mapping |
| `METALS_YAHOO_UNIT` | see config | Unit Yahoo Finance returns per ticker |
| `METALS_TO_MT_FACTOR` | copper: 2204.6226, others: 1.0 | Multiplier to convert to USD/MT |
| `PRICE_UNIT` | `USD/MT` | Canonical price unit stored in chunks and used in prompts |
| `VALID_UNITS` | metric_ton/kg/pound/lot | Units accepted by `/predict` |
| `CHUNK_WINDOW` | 7 | Days per chunk |
| `CHUNK_OVERLAP` | 3 | Overlap between chunks |
| `EMBEDDING_MODEL` | text-embedding-3-small | OpenAI embedding model |
| `EMBEDDING_DIMENSION` | 1536 | Vector size |
| `LLM_MODEL` | gpt-4o-mini | Chat model for predictions |
| `COLLECTION_NAME` | metal_prices | Qdrant collection name |
| `QDRANT_PATH` | ./qdrant_storage | Local storage path (embedded mode only) |
| `DATA_PERIOD` | 5y | Historical data window (first ingest only) |
