import requests
import pandas as pd
import time
import os
from tqdm import tqdm

DATA_DIR = "data/2025-26"
GW_DIR = f"{DATA_DIR}/gws"

os.makedirs(GW_DIR, exist_ok=True)

def fetch_all_gws_2025_26(delay=0.3):
    print("📡 Fetching season info...")
    bootstrap = requests.get(
        "https://fantasy.premierleague.com/api/bootstrap-static/",
        timeout=10
    ).json()

    events = bootstrap["events"]

    available_gws = [e["id"] for e in events if e["finished"] or e["data_checked"]]

    if not available_gws:
        print("❌ No GWs available yet.")
        return

    print(f"📅 Available GWs: {available_gws}")

    fixtures = pd.read_csv(f"{DATA_DIR}/fixtures.csv")

    for gw in tqdm(available_gws, desc="Downloading GWs"):
        url = f"https://fantasy.premierleague.com/api/event/{gw}/live/"
        r = requests.get(url)
        r.raise_for_status()
        gw_json = r.json()

        rows = []
        for p in gw_json["elements"]:
            stats = p["stats"]

            row = {
                "element": p["id"],
                "minutes": stats["minutes"],
                "goals_scored": stats["goals_scored"],
                "assists": stats["assists"],
                "clean_sheets": stats["clean_sheets"],
                "goals_conceded": stats["goals_conceded"],
                "yellow_cards": stats["yellow_cards"],
                "red_cards": stats["red_cards"],
                "total_points": stats["total_points"],
                "influence": stats["influence"],
                "creativity": stats["creativity"],
                "threat": stats["threat"],
                "ict_index": stats["ict_index"],
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        # Add Gameweek + season
        df["Gameweek"] = gw
        df["season"] = "2025-26"

        # Merge with players_raw to get player names
        pr = pd.read_csv(f"{DATA_DIR}/players_raw.csv")
        pr = pr.rename(columns={"element": "element"})
        pr["name"] = pr["first_name"] + " " + pr["second_name"]

        df = df.merge(pr[["element", "name", "team"]], on="element", how="left")

        # ===== Opponent reconstruction from fixtures =====
        gw_fx = fixtures[fixtures["event"] == gw]

        opp_rows = []
        for _, fx in gw_fx.iterrows():
            h = fx["team_h"]
            a = fx["team_a"]

            opp_rows.append({"team": h, "opponent_team": a, "was_home": True})
            opp_rows.append({"team": a, "opponent_team": h, "was_home": False})

        df_opp = pd.DataFrame(opp_rows)

        df = df.merge(df_opp, on="team", how="left")

        # Save
        out_path = f"{GW_DIR}/gw{gw}.csv"
        df.to_csv(out_path, index=False, encoding="utf-8-sig")

        print(f"💾 Saved → {out_path}")

        time.sleep(delay)

    print("🎉 All GW files created successfully!")

if __name__ == "__main__":
    fetch_all_gws_2025_26()
