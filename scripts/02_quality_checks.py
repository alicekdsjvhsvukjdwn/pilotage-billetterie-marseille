# scripts/02_quality_checks.py
from __future__ import annotations

from pathlib import Path
import pandas as pd


RAW_DIR = Path("data/raw")
DOCS_DIR = Path("docs")


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    events_p = RAW_DIR / "events.csv"
    tx_p = RAW_DIR / "transactions.csv"
    att_p = RAW_DIR / "attendance.csv"

    missing = [p for p in [events_p, tx_p, att_p] if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Fichiers manquants dans data/raw: {', '.join(str(p) for p in missing)}")

    events = pd.read_csv(events_p)
    tx = pd.read_csv(tx_p)
    att = pd.read_csv(att_p)

    checks = []

    # Duplicats
    dup_tx = tx.duplicated(subset=["tx_id"]).sum()
    dup_events = events.duplicated(subset=["event_id"]).sum()
    checks.append(("Duplicats tx_id", int(dup_tx)))
    checks.append(("Duplicats event_id", int(dup_events)))

    # Valeurs manquantes (top 10 colonnes)
    na_tx = tx.isna().sum().sort_values(ascending=False)
    na_events = events.isna().sum().sort_values(ascending=False)

    # Cohérence dates
    tx["purchase_date"] = pd.to_datetime(tx["purchase_date"], errors="coerce")
    tx["event_date"] = pd.to_datetime(tx["event_date"], errors="coerce")
    bad_dates = (tx["purchase_date"] > tx["event_date"]).sum()
    checks.append(("Achat après event_date", int(bad_dates)))

    # Prix et quantités
    bad_price = (tx["ticket_price"] <= 0).sum()
    bad_qty = (tx["qty"] <= 0).sum()
    checks.append(("Prix <= 0", int(bad_price)))
    checks.append(("Qty <= 0", int(bad_qty)))

    # Attendance cohérence
    bad_att = ((att["attended_qty"] > att["qty"]) | (att["attended_qty"] < 0)).sum()
    checks.append(("Attendance incohérente", int(bad_att)))

    report = []
    report.append("# Data Quality Report — Pilotage Billetterie (synthetic)\n")
    report.append("## Fichiers\n")
    report.append(f"- events: {len(events)} lignes\n")
    report.append(f"- transactions: {len(tx)} lignes\n")
    report.append(f"- attendance: {len(att)} lignes\n")

    report.append("\n## Checks\n")
    for label, value in checks:
        status = "✅" if value == 0 else "⚠️"
        report.append(f"- {status} **{label}**: {value}\n")

    report.append("\n## Valeurs manquantes (top)\n")
    report.append("### transactions\n")
    report.append(na_tx.head(10).to_string() + "\n")
    report.append("\n### events\n")
    report.append(na_events.head(10).to_string() + "\n")

    out = DOCS_DIR / "data_quality_report.md"
    out.write_text("\n".join(report), encoding="utf-8")
    print("✅ Report written:", out.resolve())


if __name__ == "__main__":
    main()
