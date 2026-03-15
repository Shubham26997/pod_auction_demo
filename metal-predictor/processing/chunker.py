from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from config import CHUNK_OVERLAP, CHUNK_WINDOW, PRICE_UNIT

# Data older than this is aggregated into monthly summaries instead of
# fine-grained weekly windows.
MONTHLY_CUTOFF_YEARS = 2


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _iso_to_timestamp(date_str: str) -> float:
    """Convert a YYYY-MM-DD string to a UTC Unix timestamp (float)."""
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


# ---------------------------------------------------------------------------
# Weekly chunking  (recent data — last MONTHLY_CUTOFF_YEARS years)
# ---------------------------------------------------------------------------

def create_weekly_chunks(
    df: pd.DataFrame,
    metal_name: str,
    window: int = CHUNK_WINDOW,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """
    Slice a metal price DataFrame into overlapping weekly windows.

    Metadata includes a 'granularity' field set to 'weekly' and an
    'end_timestamp' Unix float for efficient Qdrant Range filtering.
    """
    chunks: list[dict[str, Any]] = []

    if len(df) < window:
        print(
            f"  [!] Not enough rows for {metal_name} "
            f"(need {window}, have {len(df)}) — skipping"
        )
        return chunks

    step = window - overlap

    for start_idx in range(0, len(df) - window + 1, step):
        chunk_df = df.iloc[start_idx : start_idx + window]

        start_date = chunk_df.index[0].strftime("%Y-%m-%d")
        end_date = chunk_df.index[-1].strftime("%Y-%m-%d")

        open_price = round(float(chunk_df["Open"].iloc[0]), 4)
        close_price = round(float(chunk_df["Close"].iloc[-1]), 4)
        high_price = round(float(chunk_df["High"].max()), 4)
        low_price = round(float(chunk_df["Low"].min()), 4)
        weekly_change = round(float(chunk_df["pct_change"].sum()), 2)
        trend = "bullish" if weekly_change >= 0 else "bearish"
        avg_volume = round(float(chunk_df["avg_volume"].mean()), 2)
        volatility = round(float(chunk_df["volatility"].mean()), 4)

        text = (
            f"Metal: {metal_name} | Week: {start_date} to {end_date} | "
            f"Open: {open_price} {PRICE_UNIT} | Close: {close_price} {PRICE_UNIT} | "
            f"High: {high_price} {PRICE_UNIT} | Low: {low_price} {PRICE_UNIT} | "
            f"Weekly Change: {weekly_change}% | Trend: {trend} | "
            f"Avg Volume: {avg_volume} | Volatility: {volatility}"
        )

        metadata = {
            "metal": metal_name,
            "granularity": "weekly",           # tiered chunking marker
            "price_unit": PRICE_UNIT,          # LME standard: USD/MT
            "start_date": start_date,
            "end_date": end_date,
            "end_timestamp": _iso_to_timestamp(end_date),   # for Qdrant Range filter
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "pct_change": weekly_change,
            "trend": trend,
            "avg_volume": avg_volume,
            "volatility": volatility,
        }

        chunks.append({"text": text, "metadata": metadata})

    return chunks


# ---------------------------------------------------------------------------
# Monthly chunking  (historical data — older than MONTHLY_CUTOFF_YEARS)
# ---------------------------------------------------------------------------

def create_monthly_summary_chunks(
    df: pd.DataFrame,
    metal_name: str,
) -> list[dict[str, Any]]:
    """
    Resample a DataFrame of old price data (older than MONTHLY_CUTOFF_YEARS)
    into one chunk per calendar month.

    Monthly chunks are coarser than weekly ones but preserve long-term trend
    and volatility signals without bloating the vector DB with redundant
    fine-grained windows for data that is no longer actionable.

    Metadata includes 'granularity': 'monthly' and 'end_timestamp' for
    date-range pre-filtering on retrieval.
    """
    if df.empty:
        return []

    # Resample to month-end periods
    monthly: pd.DataFrame = df.resample("ME").agg(
        {
            "Open": "first",
            "Close": "last",
            "High": "max",
            "Low": "min",
            "pct_change": "sum",       # total change over the month
            "volatility": "mean",
            "avg_volume": "mean",
        }
    ).dropna()

    if monthly.empty:
        return []

    chunks: list[dict[str, Any]] = []

    for idx, row in monthly.iterrows():
        month_label = idx.strftime("%Y-%m")
        # First calendar day of the month
        start_date = idx.to_period("M").to_timestamp().strftime("%Y-%m-%d")
        # Last calendar day of the month (the resample index is month-end)
        end_date = idx.strftime("%Y-%m-%d")

        open_price = round(float(row["Open"]), 4)
        close_price = round(float(row["Close"]), 4)
        high_price = round(float(row["High"]), 4)
        low_price = round(float(row["Low"]), 4)
        monthly_change = round(float(row["pct_change"]), 2)
        trend = "bullish" if monthly_change >= 0 else "bearish"
        avg_volume = round(float(row["avg_volume"]), 2)
        volatility = round(float(row["volatility"]), 4)

        text = (
            f"Metal: {metal_name} | Month: {month_label} | "
            f"Open: {open_price} {PRICE_UNIT} | Close: {close_price} {PRICE_UNIT} | "
            f"High: {high_price} {PRICE_UNIT} | Low: {low_price} {PRICE_UNIT} | "
            f"Monthly Change: {monthly_change}% | Trend: {trend} | "
            f"Avg Volume: {avg_volume} | Volatility: {volatility}"
        )

        metadata = {
            "metal": metal_name,
            "granularity": "monthly",          # tiered chunking marker
            "price_unit": PRICE_UNIT,          # LME standard: USD/MT
            "start_date": start_date,
            "end_date": end_date,
            "end_timestamp": _iso_to_timestamp(end_date),   # for Qdrant Range filter
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "pct_change": monthly_change,
            "trend": trend,
            "avg_volume": avg_volume,
            "volatility": volatility,
        }

        chunks.append({"text": text, "metadata": metadata})

    return chunks


# ---------------------------------------------------------------------------
# Batch helper  (tiered: monthly for old, weekly for recent)
# ---------------------------------------------------------------------------

def chunk_all_metals(metal_data_dict: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """
    Create tiered chunks for every metal in the supplied dict.

    Strategy
    --------
    - Data older than MONTHLY_CUTOFF_YEARS years  → monthly summary chunks
    - Data within the last MONTHLY_CUTOFF_YEARS years → weekly overlapping chunks

    Returns a flat list of all chunks (both granularities) across all metals.
    """
    cutoff: datetime = datetime.now(tz=timezone.utc) - timedelta(
        days=365 * MONTHLY_CUTOFF_YEARS
    )

    all_chunks: list[dict[str, Any]] = []

    for metal_name, df in metal_data_dict.items():
        # Ensure index is tz-aware for comparison
        if df.index.tzinfo is None:
            idx = df.index.tz_localize("UTC")
        else:
            idx = df.index

        recent_df = df[idx >= cutoff]
        old_df = df[idx < cutoff]

        weekly_chunks = create_weekly_chunks(recent_df, metal_name) if not recent_df.empty else []
        monthly_chunks = create_monthly_summary_chunks(old_df, metal_name) if not old_df.empty else []

        all_chunks.extend(weekly_chunks)
        all_chunks.extend(monthly_chunks)

        print(
            f"  Chunking {metal_name}: "
            f"{len(weekly_chunks)} weekly (≤{MONTHLY_CUTOFF_YEARS}y) + "
            f"{len(monthly_chunks)} monthly (>{MONTHLY_CUTOFF_YEARS}y)"
        )

    return all_chunks
