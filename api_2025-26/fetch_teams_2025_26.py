# api_2025-26/fetch_teams_2025_26.py

import requests
import pandas as pd
import os

def fetch_teams_2025_26(save_path="data/2025-26/teams.csv"):
    print("📡 Fetching teams from FPL API (bootstrap-static)...")

    BASE_URL = "https://fantasy.premierleague.com/api/"

    try:
        bootstrap = requests.get(BASE_URL + "bootstrap-static/", timeout=10).json()

        teams = [
            {
                "id": t["id"],
                "name": t["name"],
                "short_name": t["short_name"]
            }
            for t in bootstrap["teams"]
        ]

        df = pd.DataFrame(teams)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df.to_csv(save_path, index=False, encoding="utf-8")

        print(f"✅ Saved teams.csv → {save_path}")
        print(df.head())

    except Exception as e:
        print(f"❌ ERROR fetching teams: {e}")


if __name__ == "__main__":
    fetch_teams_2025_26()
