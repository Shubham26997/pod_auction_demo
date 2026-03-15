from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import DATA_PERIOD, DATA_START_DATE, METALS, METALS_TO_MT_FACTOR, PRICE_UNIT


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _add_derived_metrics(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Flatten MultiIndex columns (yfinance >=0.2), keep OHLCV, and add
    pct_change, volatility, avg_volume.  Returns empty DataFrame on bad input.
    """
    if raw is None or raw.empty:
        print(f"  [!] No data returned for ticker '{ticker}'")
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] for col in raw.columns]

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(raw.columns)
    if missing:
        print(f"  [!] Missing columns {missing} for '{ticker}'")
        return pd.DataFrame()

    df = raw[list(required)].copy()
    df["pct_change"] = df["Close"].pct_change() * 100
    df["volatility"] = df["Close"].pct_change().rolling(7).std() * 100
    df["avg_volume"] = df["Volume"].rolling(7).mean()
    df = df.dropna()
    return df


# ---------------------------------------------------------------------------
# Public fetch functions
# ---------------------------------------------------------------------------

def fetch_metal_data(ticker: str, period: str = DATA_PERIOD) -> pd.DataFrame:
    """
    Fetch historical OHLCV data using a yfinance period string (e.g. '5y', '1y').
    Used for the very first full ingest when no start date is configured.
    """
    try:
        raw = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        return _add_derived_metrics(raw, ticker)
    except Exception as exc:
        print(f"  [!] Error fetching '{ticker}' (period={period}): {exc}")
        return pd.DataFrame()


def fetch_metal_data_from(ticker: str, start_date: str, end_date: str | None = None) -> pd.DataFrame:
    """
    Fetch OHLCV data for a specific calendar date range.

    start_date : ISO string "YYYY-MM-DD"
    end_date   : ISO string, defaults to today if omitted.

    For incremental updates we fetch from (last_ingested_date - CHUNK_WINDOW)
    so the chunker has enough context rows to form complete 7-day windows even
    at the boundary.  Callers are responsible for passing the adjusted start.
    """
    try:
        raw = yf.download(
            ticker,
            start=start_date,
            end=end_date,          # None → yfinance uses today
            progress=False,
            auto_adjust=True,
        )
        return _add_derived_metrics(raw, ticker)
    except Exception as exc:
        print(f"  [!] Error fetching '{ticker}' from {start_date}: {exc}")
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------

def fetch_all_metals(
    since_dates: dict[str, str] | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Fetch data for every metal in config.METALS.

    since_dates : optional {metal_name: "YYYY-MM-DD"} of the last stored
                  end_date per metal (used for incremental updates).
                  Metals missing from the dict use the global initial config.

    Returns {metal_name: DataFrame}; metals with no usable data are omitted.
    """
    from config import CHUNK_WINDOW  # avoid circular at module level

    metal_data: dict[str, pd.DataFrame] = {}

    for metal_name, ticker in METALS.items():
        last_date = (since_dates or {}).get(metal_name)

        if last_date:
            # Pull slightly before the last stored date so the chunker can
            # build complete windows across the boundary (overlap context).
            adjusted_start = (
                datetime.strptime(last_date, "%Y-%m-%d") - timedelta(days=CHUNK_WINDOW * 2)
            ).strftime("%Y-%m-%d")
            print(f"  Fetching {metal_name} ({ticker}) incrementally from {adjusted_start} …")
            df = fetch_metal_data_from(ticker, start_date=adjusted_start)
        elif DATA_START_DATE:
            print(f"  Fetching {metal_name} ({ticker}) from {DATA_START_DATE} …")
            df = fetch_metal_data_from(ticker, start_date=DATA_START_DATE)
        else:
            print(f"  Fetching {metal_name} ({ticker}) period={DATA_PERIOD} …")
            df = fetch_metal_data(ticker, period=DATA_PERIOD)

        if not df.empty:
            # Normalise OHLC prices to LME standard (USD/MT).
            # pct_change, volatility, and avg_volume are dimensionless
            # ratios / counts — they do not need unit conversion.
            factor = METALS_TO_MT_FACTOR[metal_name]
            if factor != 1.0:
                for col in ("Open", "High", "Low", "Close"):
                    df[col] = df[col] * factor
                print(
                    f"    -> normalised {metal_name} prices to {PRICE_UNIT} "
                    f"(× {factor})"
                )
            metal_data[metal_name] = df
            print(f"    -> {len(df)} rows retrieved")
        else:
            print(f"    -> Skipping {metal_name} (no usable data)")

    return metal_data
