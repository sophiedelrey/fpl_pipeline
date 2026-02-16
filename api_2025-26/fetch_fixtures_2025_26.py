import requests
import pandas as pd
import os

OUTPUT_PATH = "data/2025-26/fixtures.csv"

def fetch_fixtures_2025_26():
    print("📡 Fetching fixtures from FPL API...")

    url = "https://fantasy.premierleague.com/api/fixtures/"

    r = requests.get(url, timeout=10)
    r.raise_for_status()

    data = r.json()
    df = pd.DataFrame(data)

    # Keep only columns matching vaastav format
    keep = [
        "id",
        "event",
        "team_h", "team_a",
        "team_h_difficulty", "team_a_difficulty",
        "kickoff_time"
    ]

    df = df[keep].copy()

    # Convert event to numeric (it may be null for future GWs)
    df["event"] = pd.to_numeric(df["event"], errors="coerce")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"✅ Saved fixtures.csv → {OUTPUT_PATH}")
    print(df.head())

if __name__ == "__main__":
    fetch_fixtures_2025_26()
