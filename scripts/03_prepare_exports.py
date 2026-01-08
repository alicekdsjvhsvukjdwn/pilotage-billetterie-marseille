# scripts/03_prepare_exports.py
from __future__ import annotations

from pathlib import Path
import pandas as pd


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    events = pd.read_csv(RAW_DIR / "events.csv")
    tx = pd.read_csv(RAW_DIR / "transactions.csv")
    att = pd.read_csv(RAW_DIR / "attendance.csv")

    # Parse dates
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce")
    tx["purchase_date"] = pd.to_datetime(tx["purchase_date"], errors="coerce")
    tx["event_date"] = pd.to_datetime(tx["event_date"], errors="coerce")
    att["event_date"] = pd.to_datetime(att["event_date"], errors="coerce")

    # Merge
    bi = tx.merge(events, on="event_id", how="left", suffixes=("", "_ev"))
    bi = bi.merge(att[["tx_id", "no_show", "attended_qty"]], on="tx_id", how="left")

    # KPI helper columns
    bi["purchase_day"] = bi["purchase_date"].dt.date.astype(str)
    bi["event_day"] = bi["event_date"].dt.date.astype(str)
    bi["is_early"] = (bi["days_before_event"] > 45).astype(int)
    bi["is_late"] = (bi[" days_before_event"] <= 7).astype(int)

    out = PROCESSED_DIR / "billetterie_bi.csv"
    bi.to_csv(out, index=False, encoding="utf-8")
    print("✅ BI export:", out.resolve(), f"({len(bi)} lignes)")


if __name__ == "__main__":
    main()
