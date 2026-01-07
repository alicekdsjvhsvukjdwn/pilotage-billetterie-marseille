# scripts/01_generate_data.py
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


RAW_DIR = Path("data/raw")


def make_events(rng: np.random.Generator, year=2026) -> pd.DataFrame:
    events = [
        # (event_id, name, venue, capacity, base_price, category)
        ("EVT001", "Festival — Soirée Electro", "Friche la Belle de Mai", 1600, 29, "festival"),
        ("EVT002", "Rap Live — Salle", "Espace Julien", 1200, 25, "salle"),
        ("EVT003", "Pop/Indé — Salle", "Le Makeda", 450, 18, "salle"),
        ("EVT004", "DJ Set — Club", "Le Cabaret Aléatoire", 700, 22, "club"),
        ("EVT005", "Open Air — Electro", "Parc Borély", 3000, 24, "festival"),
        ("EVT006", "Stand-up — Salle", "CEPAC Silo", 1800, 32, "salle"),
    ]
    df = pd.DataFrame(events, columns=["event_id", "event_name", "venue", "capacity", "base_price", "category"])

    # Dates d'événement (échelonnées)
    start = pd.Timestamp(f"{year}-03-15")
    gaps = rng.integers(10, 28, size=len(df))
    df["event_date"] = start + pd.to_timedelta(np.cumsum(gaps), unit="D")
    return df


def make_transactions(rng: np.random.Generator, events: pd.DataFrame, n_tx=25000) -> pd.DataFrame:
    # Répartition des ventes par event proportionnelle à la capacité
    weights = events["capacity"].to_numpy(dtype=float)
    weights = weights / weights.sum()

    chosen_events = rng.choice(events["event_id"], size=n_tx, p=weights)
    df = pd.DataFrame({"tx_id": [f"TX{str(i).zfill(6)}" for i in range(1, n_tx + 1)], "event_id": chosen_events})

    ev_map = events.set_index("event_id").to_dict(orient="index")
    df["event_date"] = df["event_id"].map(lambda x: ev_map[x]["event_date"])
    df["venue"] = df["event_id"].map(lambda x: ev_map[x]["venue"])
    df["capacity"] = df["event_id"].map(lambda x: ev_map[x]["capacity"])
    df["base_price"] = df["event_id"].map(lambda x: ev_map[x]["base_price"])
    df["category"] = df["event_id"].map(lambda x: ev_map[x]["category"])

    # Timing d’achat : la majorité achète avant, avec queue “last minute”
    # days_before_event ∈ [0..120]
    days_before = np.clip((rng.gamma(shape=2.2, scale=12, size=n_tx)).astype(int), 0, 120)
    # inverser pour avoir plus de ventes “loin” et un pic “près”
    days_before = np.clip(120 - days_before, 0, 120)
    df["purchase_date"] = df["event_date"] - pd.to_timedelta(days_before, unit="D")
    df["days_before_event"] = days_before

    # Canaux
    channels = np.array(["web", "partenaires", "guichet"])
    p = np.array([0.72, 0.18, 0.10])
    df["channel"] = rng.choice(channels, size=n_tx, p=p)

    # Typologie public (local/touriste)
    df["audience_type"] = rng.choice(["local", "touriste"], size=n_tx, p=[0.78, 0.22])

    # Tarif (early/regular/late + réduits)
    # Early si achat > 45 jours avant, late si <= 7 jours
    def price_mult(d):
        if d > 45:
            return 0.85
        if d <= 7:
            return 1.10
        return 1.00

    mult = np.vectorize(price_mult)(df["days_before_event"].to_numpy())
    # Réductions
    discounts = rng.choice(["plein", "reduit", "etudiant"], size=n_tx, p=[0.75, 0.15, 0.10])
    df["fare_type"] = discounts
    disc_mult = np.where(discounts == "plein", 1.00, np.where(discounts == "reduit", 0.80, 0.70))

    # Prix final + bruit léger
    price = df["base_price"].to_numpy() * mult * disc_mult
    price = price * rng.normal(1.0, 0.03, size=n_tx)
    df["ticket_price"] = np.round(np.clip(price, 8, None), 2)

    # Nb billets par transaction (panier)
    # Web a tendance à avoir panier un poil plus haut
    lam = np.where(df["channel"].to_numpy() == "web", 1.25, 1.12)
    baskets = rng.poisson(lam=lam, size=n_tx) + 1
    baskets = np.clip(baskets, 1, 6)
    df["qty"] = baskets

    df["revenue"] = np.round(df["ticket_price"] * df["qty"], 2)

    # Géographie (fictif mais “Marseille vibe”)
    zones = ["13001", "13002", "13003", "13004", "13005", "13006", "13007", "13008", "13009", "13010", "13011", "13012", "13013", "13014", "13015", "13016", "Aubagne", "La Ciotat", "Aix", "Autres"]
    z_p = np.array([0.05,0.04,0.04,0.05,0.06,0.10,0.05,0.10,0.06,0.05,0.05,0.05,0.04,0.04,0.04,0.04,0.03,0.03,0.04,0.05])
    z_p = z_p / z_p.sum()
    df["geo_zone"] = rng.choice(zones, size=n_tx, p=z_p)

    return df


def make_attendance(rng: np.random.Generator, tx: pd.DataFrame) -> pd.DataFrame:
    # No-show plus fréquent quand achat très early + partenaire (hypothèse plausible)
    early = tx["days_before_event"].to_numpy() > 60
    partner = tx["channel"].to_numpy() == "partenaires"
    base_ns = 0.04
    p_ns = base_ns + 0.03 * early + 0.02 * partner
    no_show = rng.random(size=len(tx)) < p_ns
    att = tx[["tx_id", "event_id", "event_date", "qty"]].copy()
    att["no_show"] = no_show.astype(int)
    # Si no-show, on considère toute la transaction no-show (simple)
    att["attended_qty"] = np.where(att["no_show"].to_numpy() == 1, 0, att["qty"].to_numpy())
    return att


def main(seed=42):
    rng = np.random.default_rng(seed)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    events = make_events(rng)
    tx = make_transactions(rng, events, n_tx=25000)
    att = make_attendance(rng, tx)

    events.to_csv(RAW_DIR / "events.csv", index=False, encoding="utf-8")
    tx.to_csv(RAW_DIR / "transactions.csv", index=False, encoding="utf-8")
    att.to_csv(RAW_DIR / "attendance.csv", index=False, encoding="utf-8")

    print("✅ Data generated:")
    print(" -", (RAW_DIR / "events.csv").resolve())
    print(" -", (RAW_DIR / "transactions.csv").resolve())
    print(" -", (RAW_DIR / "attendance.csv").resolve())
    print(f"   events={len(events)} tx={len(tx)} attendance={len(att)}")


if __name__ == "__main__":
    main()
