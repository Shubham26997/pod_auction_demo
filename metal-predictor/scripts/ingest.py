#!/usr/bin/env python3
"""
Ingestion script — populate or incrementally update the Qdrant vector DB.

Usage
-----
  uv run python scripts/ingest.py              # incremental (default)
  uv run python scripts/ingest.py --full       # wipe and rebuild from scratch

Incremental mode (default)
  - Reads the latest stored end_date per metal from Qdrant.
  - Fetches only the new trading days since that date.
  - Appends the new chunks — existing vectors are untouched.
  - Safe to run on a daily cron; if nothing is new, it exits cleanly.

Full mode  (--full)
  - Deletes the entire collection and rebuilds it from scratch.
  - Respects DATA_START_DATE / DATA_PERIOD from .env / environment.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from data.data_collector import fetch_all_metals
from embeddings.embedder import get_embedder
from processing.chunker import chunk_all_metals
from vectorstore.qdrant_store import (
    append_chunks,
    collection_exists,
    get_latest_ingested_dates,
    init_vectorstore,
    load_vectorstore,
    get_retriever,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filter_new_chunks(
    chunks: list[dict],
    latest_dates: dict[str, str],
) -> list[dict]:
    """
    Drop any chunk whose end_date is already stored in Qdrant.
    This prevents duplicates when fetching with the overlap window.
    """
    if not latest_dates:
        return chunks

    new_chunks = []
    for chunk in chunks:
        metal = chunk["metadata"]["metal"]
        end_date = chunk["metadata"]["end_date"]
        last_stored = latest_dates.get(metal)
        if last_stored is None or end_date > last_stored:
            new_chunks.append(chunk)

    return new_chunks


# ---------------------------------------------------------------------------
# Ingest modes
# ---------------------------------------------------------------------------

def run_full_ingest() -> None:
    """Wipe the collection and rebuild everything from scratch."""
    print("\n[1/4] Fetching full historical data …")
    metal_data = fetch_all_metals()          # no since_dates → uses DATA_PERIOD / DATA_START_DATE
    if not metal_data:
        print("ERROR: No metal data fetched.")
        sys.exit(1)

    print("\n[2/4] Creating weekly chunks …")
    chunks = chunk_all_metals(metal_data)
    if not chunks:
        print("ERROR: No chunks produced.")
        sys.exit(1)
    print(f"  Total chunks: {len(chunks)}")

    print("\n[3/4] Initialising embedder …")
    embedder = get_embedder()

    print(f"\n[4/4] Embedding and storing {len(chunks)} chunks in Qdrant …")
    init_vectorstore(chunks, embedder)

    print(f"\n  Done — {len(chunks)} vectors stored (full reset).")


def run_incremental_ingest() -> None:
    """Append only trading days newer than what is already in Qdrant."""
    print("\n[1/5] Checking existing Qdrant data …")
    latest_dates = get_latest_ingested_dates()

    if not latest_dates:
        print("  No existing data found — falling back to full ingest.")
        run_full_ingest()
        return

    print("  Latest stored end_date per metal:")
    for metal, date in sorted(latest_dates.items()):
        print(f"    {metal}: {date}")

    print("\n[2/5] Fetching new trading days …")
    metal_data = fetch_all_metals(since_dates=latest_dates)
    if not metal_data:
        print("  No new data fetched — collection is already up to date.")
        return

    print("\n[3/5] Creating weekly chunks from new data …")
    all_new_chunks = chunk_all_metals(metal_data)

    print("\n[4/5] Filtering out already-stored chunks …")
    new_chunks = _filter_new_chunks(all_new_chunks, latest_dates)

    if not new_chunks:
        print("  Nothing new to add — already up to date.")
        return

    by_metal: dict[str, int] = {}
    for c in new_chunks:
        by_metal[c["metadata"]["metal"]] = by_metal.get(c["metadata"]["metal"], 0) + 1
    print("  New chunks per metal:")
    for metal, count in sorted(by_metal.items()):
        print(f"    {metal}: {count}")

    print(f"\n[5/5] Embedding and appending {len(new_chunks)} new chunks …")
    embedder = get_embedder()
    append_chunks(new_chunks, embedder)

    print(f"\n  Done — {len(new_chunks)} new vectors appended.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Metal price data ingestion")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Wipe the Qdrant collection and rebuild from scratch",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Metal Price Prediction — Data Ingestion")
    mode = "FULL RESET" if args.full else "INCREMENTAL"
    print(f"  Mode: {mode}")
    print("=" * 60)

    if args.full:
        run_full_ingest()
    else:
        run_incremental_ingest()

    print("=" * 60)


if __name__ == "__main__":
    main()
