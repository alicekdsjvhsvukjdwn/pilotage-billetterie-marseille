# scripts/01_generate_data.py
from __future__ import annotations

import random
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# -----------------------------
# Config simple (tu peux ajuster)
# -----------------------------
SEED = 42
N_EVENTS = 24
TARGET_TRANSACTIONS = 9000  # transactions (pas tickets)
START_DATE = "2026-03-01"   # période des événements
END_DATE = "2026-06-30"
OUTPUT_DIR = Path("data/raw")


# Marseille (fictif mais crédible)
ZONES = [
    "Vieux-Port", "Le Panier", "Noailles", "La Plaine", "Cours Julien",
    "Castellane", "Prado", "Endoume", "Les Goudes", "L’Estaque",
    "Belle de Mai", "Saint-Charles", "La Joliette", "Euroméditerranée",
    "La Timone", "Mazargues", "Pointe Rouge", "Saint-Loup", "Saint-Barnabé"
]

VENUES = [
    "Salle du Vieux-Port", "Théâtre du Panier", "La Friche (scène)", "Le Dôme (club)",
    "Dock des Suds (fiction)", "Espace Joliette", "Théâtre Canebière", "Salle Prado"
]

GENRES = [
    "Concert", "Théâtre", "Stand-up", "Festival", "Projection", "Conférence", "Danse"
]

CHANNELS = ["web", "partenaire", "guichet", "pass"]
TARIFFS = ["plein", "reduit", "early_bird", "last_minute"]


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def pick_weighted(values, weights, size=1):
    return random.choices(values, weights=weights, k=size)


def dt_range(start: datetime, end: datetime) -> datetime:
    """Random datetime in [start, end]."""
    delta = end - start
    sec = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=sec)


def main() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    ensure_dir(OUTPUT_DIR)

    start_dt = datetime.fromisoformat(START_DATE)
    end_dt = datetime.fromisoformat(END_DATE)

    # -----------------------------
    # 1) events.csv
    # -----------------------------
    events = []
    for i in range(1, N_EVENTS + 1):
        event_id = f"E{i:03d}"

        genre = random.choice(GENRES)
        venue = random.choice(VENUES)
        zone = random.choice(ZONES)

        # date/heure de séance
        event_dt = dt_range(start_dt, end_dt).replace(minute=0, second=0, microsecond=0)
        # plutôt soir / week-end
        hour = random.choice([18, 19, 20, 21])
        event_dt = event_dt.replace(hour=hour)

        capacity = int(np.random.choice([150, 250, 400, 700, 1200, 2000], p=[.10, .18, .22, .20, .18, .12]))
        base_price = float(np.random.choice([12, 15, 18, 22, 28, 35, 45], p=[.10, .18, .20, .20, .16, .10, .06]))

        event_name = f"{genre} — Session {i}"

        events.append(
            dict(
                event_id=event_id,
                event_name=event_name,
                venue_name=venue,
                date_time=event_dt.isoformat(sep=" "),
                capacity=capacity,
                base_price=base_price,
                genre=genre,
                quartier_zone=zone,
            )
        )

    df_events = pd.DataFrame(events).sort_values("date_time").reset_index(drop=True)

    # -----------------------------
    # 2) transactions.csv
    # -----------------------------
    # On génère des transactions par événement, proportionnel à la capacité
    tx_rows = []
    tx_id = 1

    # Params pricing
    tariff_multiplier = {
        "plein": 1.00,
        "reduit": 0.80,
        "early_bird": 0.75,
        "last_minute": 0.90,
    }
    channel_fee = {  # petits effets, juste pour realism
        "web": 1.00,
        "partenaire": 1.02,
        "guichet": 1.00,
        "pass": 0.00,  # pass: prix géré différemment ci-dessous
    }

    # buyer_geo
    geo_values = ["local", "touriste"]
    geo_weights = [0.78, 0.22]  # Marseille = beaucoup de locaux

    # lead-time distribution (jours avant l'événement)
    # early_bird -> achats plus tôt, last_minute -> achats tardifs
    def sample_lead_time(tariff: str) -> int:
        if tariff == "early_bird":
            return int(np.clip(np.random.normal(35, 12), 7, 90))
        if tariff == "last_minute":
            return int(np.clip(np.random.normal(2, 2), 0, 10))
        # plein / réduit
        return int(np.clip(np.random.normal(14, 10), 0, 60))

    # tickets qty distribution (1-4 la plupart du temps)
    def sample_qty() -> int:
        return int(np.random.choice([1, 2, 3, 4, 5], p=[0.52, 0.30, 0.12, 0.05, 0.01]))

    # For each event, generate target transactions proportional to capacity, with noise
    cap_sum = df_events["capacity"].sum()
    base_targets = (df_events["capacity"] / cap_sum * TARGET_TRANSACTIONS).values

    for idx, ev in df_events.iterrows():
        n_tx = int(np.random.poisson(lam=max(10, base_targets[idx] * np.random.uniform(0.85, 1.15))))
        ev_dt = datetime.fromisoformat(str(ev["date_time"]))

        for _ in range(n_tx):
            tariff = pick_weighted(TARIFFS, [0.58, 0.18, 0.14, 0.10], size=1)[0]
            channel = pick_weighted(CHANNELS, [0.68, 0.12, 0.14, 0.06], size=1)[0]
            buyer_geo = pick_weighted(geo_values, geo_weights, size=1)[0]

            lead_days = sample_lead_time(tariff)
            purchase_dt = ev_dt - timedelta(days=lead_days) + timedelta(hours=random.randint(9, 21), minutes=random.choice([0, 10, 20, 30, 40, 50]))
            # évite achat après event (au cas où lead_days = 0)
            if purchase_dt > ev_dt:
                purchase_dt = ev_dt - timedelta(hours=random.randint(1, 6))

            qty = sample_qty()

            # price model
            base = float(ev["base_price"])
            if channel == "pass":
                # pass: achat "gratuit" sur transaction, on met 0 mais on garde l'info
                total = 0.0
            else:
                unit = base * tariff_multiplier[tariff] * channel_fee[channel]
                # petit bruit + arrondi
                unit = max(5.0, unit + np.random.normal(0, 0.6))
                total = round(unit * qty, 2)

            tx_rows.append(
                dict(
                    transaction_id=f"T{tx_id:06d}",
                    event_id=ev["event_id"],
                    purchase_datetime=purchase_dt.isoformat(sep=" "),
                    tickets_qty=qty,
                    price_paid_total=total,
                    channel=channel,
                    tariff=tariff,
                    buyer_geo=buyer_geo,
                    lead_time_days=lead_days,
                )
            )
            tx_id += 1

    df_tx = pd.DataFrame(tx_rows)

    # -----------------------------
    # 3) attendance.csv (optionnel mais utile)
    # -----------------------------
    # proba no-show un peu plus forte si achat très tôt, et si "touriste"
    att_rows = []
    for _, r in df_tx.iterrows():
        lead = int(r["lead_time_days"])
        geo = r["buyer_geo"]
        channel = r["channel"]

        # base attendance
        p_attend = 0.92
        if lead >= 45:
            p_attend -= 0.05
        if lead >= 75:
            p_attend -= 0.04
        if geo == "touriste":
            p_attend -= 0.03
        if channel == "pass":
            p_attend -= 0.02

        p_attend = float(np.clip(p_attend, 0.75, 0.98))
        attended = 1 if random.random() < p_attend else 0

        att_rows.append(
            dict(
                transaction_id=r["transaction_id"],
                attended=attended
            )
        )

    df_att = pd.DataFrame(att_rows)

    # -----------------------------
    # Save
    # -----------------------------
    events_path = OUTPUT_DIR / "events.csv"
    tx_path = OUTPUT_DIR / "transactions.csv"
    att_path = OUTPUT_DIR / "attendance.csv"

    df_events.to_csv(events_path, index=False, encoding="utf-8")
    df_tx.to_csv(tx_path, index=False, encoding="utf-8")
    df_att.to_csv(att_path, index=False, encoding="utf-8")

    print("✅ Génération terminée")
    print(f"- {events_path}  ({len(df_events)} lignes)")
    print(f"- {tx_path}  ({len(df_tx)} lignes)")
    print(f"- {att_path}  ({len(df_att)} lignes)")
    print("Astuce: ouvre les CSV dans Excel / Power BI ou fais un quick check avec pandas.")


if __name__ == "__main__":
    main()
