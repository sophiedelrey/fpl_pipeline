import requests
import pandas as pd
import os

OUTPUT_PATH = "data/2025-26/players_raw.csv"

def fetch_players_raw():
    print("📡 Fetching players from FPL API (bootstrap-static)...")

    url = "https://fantasy.premierleague.com/api/bootstrap-static/"

    r = requests.get(url, timeout=10)
    r.raise_for_status()

    data = r.json()
    players = data["elements"]

    df = pd.DataFrame(players)

    # Keep only columns needed to match vaastav format
    keep = [
        "id",            # element ID, matches vaastav "element"
        "team",          # team ID
        "element_type",  # position (1=GK,2=DEF,3=MID,4=FWD)
        "first_name",
        "second_name",
        "web_name"
    ]

    df = df[keep].copy()

    # Rename to match vaastav format exactly
    df.rename(columns={"id": "element"}, inplace=True)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"✅ Saved players_raw.csv → {OUTPUT_PATH}")
    print(df.head())

if __name__ == "__main__":
    fetch_players_raw()
