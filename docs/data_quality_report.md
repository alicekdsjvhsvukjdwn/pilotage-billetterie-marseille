# Data Quality Report

## Files checked
- events: `data/raw/events.csv` → 24 rows
- transactions (sample): `data/raw/transactions_sample.csv` → 5000 rows
- attendance (sample): `data/raw/attendance_sample.csv` → 5000 rows

## Headline checks

| Category | Check | Issues | Rows | Rate |
|---|---|---:|---:|---:|
| schema | events required columns present | 1 | 1 | 100.0% |
| schema | transactions required columns present | 1 | 1 | 100.0% |
| schema | attendance required columns present | 1 | 1 | 100.0% |
| duplicates | events.event_id duplicates | 0 | 24 | 0.0% |
| duplicates | transactions.transaction_id duplicates | 0 | 5000 | 0.0% |
| duplicates | attendance.transaction_id duplicates | 0 | 5000 | 0.0% |
| integrity | orphan transactions (event_id not in events) | 0 | 5000 | 0.0% |
| integrity | orphan attendance (transaction_id not in transactions) | 0 | 5000 | 0.0% |
| rules | capacity <= 0 | 0 | 24 | 0.0% |
| rules | base_price <= 0 | 0 | 24 | 0.0% |
| rules | tickets_qty <= 0 | 0 | 5000 | 0.0% |
| rules | price_paid_total <= 0 | 290 | 5000 | 5.8% |
| rules | lead_time_days < 0 | 0 | 5000 | 0.0% |
| rules | purchase after event date | 0 | 5000 | 0.0% |
| rules | attendance not in {0,1} | 0 | 5000 | 0.0% |

⚠️ Issues detected (sample files). See table above.

### Top issues (sample)
- **price_paid_total <= 0** → 290 issue(s) (5.8%)
- **events required columns present** → 1 issue(s) (100.0%)
- **transactions required columns present** → 1 issue(s) (100.0%)
- **attendance required columns present** → 1 issue(s) (100.0%)