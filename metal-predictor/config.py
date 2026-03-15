import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI API key loaded from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Supported metals and their Yahoo Finance futures ticker symbols
METALS = {
    "copper": "HG=F",
    "zinc": "ZNC=F",
    "aluminum": "ALI=F",
}

# ---------------------------------------------------------------------------
# LME (London Metal Exchange) pricing conventions
# ---------------------------------------------------------------------------
#
# LME quotes ALL base metals in USD per metric ton (USD/MT).
# Yahoo Finance, however, uses ticker-specific units:
#
#   HG=F  (copper)   → USD per pound  (lb)   — COMEX/CME convention
#   ZNC=F (zinc)     → USD per metric ton     — already LME-aligned
#   ALI=F (aluminum) → USD per metric ton     — already LME-aligned
#
# To make every stored price comparable and to match what traders enter as
# a "current LME price", we normalise all OHLC values to USD/MT at fetch
# time using METALS_TO_MT_FACTOR.
#
# Conversion: 1 metric ton = 2 204.6226 pounds  →  USD/lb × 2204.6226 = USD/MT

METALS_YAHOO_UNIT: dict[str, str] = {
    "copper":   "USD/lb",   # HG=F is quoted in US cents/lb on COMEX; yfinance returns USD/lb
    "zinc":     "USD/MT",   # ZNC=F already matches LME convention
    "aluminum": "USD/MT",   # ALI=F already matches LME convention
}

METALS_TO_MT_FACTOR: dict[str, float] = {
    "copper":   2204.6226,  # multiply USD/lb × 2204.6226 → USD/MT
    "zinc":     1.0,        # already USD/MT, no conversion needed
    "aluminum": 1.0,        # already USD/MT, no conversion needed
}

# Canonical price unit used throughout the system (chunk text, prompts, API docs)
PRICE_UNIT: str = "USD/MT"

# ---------------------------------------------------------------------------
# Valid quantity/price units accepted by the /predict endpoint
# ---------------------------------------------------------------------------
#
# These map to how commodity traders measure and quote metals:
#   metric_ton  — tonne (1 000 kg). LME standard; default unit for /predict.
#   kg          — kilogram. Useful for smaller lots or local market quotes.
#   pound       — lb. COMEX/CME standard; copper (HG=F) is quoted in USD/lb.
#   lot         — exchange contract lot. 1 CME copper lot ≈ 25 000 lbs.
#
# When calling /predict, pass current_price in the same unit you choose here.
# For LME prices (the default), always use metric_ton.

VALID_UNITS: set[str] = {"metric_ton", "kg", "pound", "lot"}

UNIT_LABELS: dict[str, str] = {
    "metric_ton": "metric ton",
    "kg":         "kilogram",
    "pound":      "pound",
    "lot":        "lot (exchange contract)",
}

# Chunking parameters: 7-day window with 3-day overlap
CHUNK_WINDOW = 7
CHUNK_OVERLAP = 3

# OpenAI model settings
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Default dimension for text-embedding-3-small
LLM_MODEL = "gpt-4o-mini"

# Qdrant vector store settings
COLLECTION_NAME = "metal_prices"
QDRANT_PATH = "./qdrant_storage"        # used only when running locally (no QDRANT_HOST)

# When QDRANT_HOST is set the client connects to a running Qdrant server
# (e.g. the qdrant container in docker-compose) instead of using embedded
# file mode.  Leave QDRANT_HOST empty for local development without Docker.
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "")      # e.g. "qdrant" or "localhost"
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

# --- Historical data window (used only on the very first ingest) ----------
#
# Two ways to set the initial lookback, checked in this order:
#   1. DATA_START_DATE="2020-01-01"  — fetch from a specific calendar date
#   2. DATA_PERIOD="2y"             — fetch a relative period (yfinance syntax:
#                                     1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max)
#
# After the first ingest, every subsequent run is INCREMENTAL — only new
# trading days since the last stored end_date are fetched and appended.
# Set the env vars to change default behaviour without touching code.
DATA_START_DATE: str = os.getenv("DATA_START_DATE", "")   # e.g. "2020-01-01"
DATA_PERIOD: str = os.getenv("DATA_PERIOD", "5y")          # fallback if no start date
