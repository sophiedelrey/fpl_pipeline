import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path("output/training_data.csv")
FIXTURES = Path("data/2018-19/fixtures.csv")

def load_fixtures():
    fx = pd.read_csv(FIXTURES)
    fx["Gameweek"] = fx["event"]
    fx["team_h"] = pd.to_numeric(fx["team_h"])
    fx["team_a"] = pd.to_numeric(fx["team_a"])
    fx["team_h_difficulty"] = pd.to_numeric(fx["team_h_difficulty"])
    fx["team_a_difficulty"] = pd.to_numeric(fx["team_a_difficulty"])
    return fx[["Gameweek", "team_h", "team_a", "team_h_difficulty", "team_a_difficulty"]]


def main():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    # Select missing difficulty for 2018-19
    mask = (df["season"] == "2018-19") & (df["Opponent Difficulty"].isna())
    missing_rows = df[mask]

    total_missing = len(missing_rows)
    print(f"Missing OD rows in 2018-19: {total_missing}")

    fx = load_fixtures()

    filled_from_fixtures = 0
    fallback_filled = 0

    # For preview of first few filled values
    preview_filled = []

    for idx, row in missing_rows.iterrows():
        gw = row["Gameweek"]
        team_id = row["Player Team ID"]
        is_home = row["Is Home"]

        if pd.isna(gw) or pd.isna(team_id) or pd.isna(is_home):
            continue

        gw = int(gw)

        # Try filling from fixtures
        if is_home:
            rnd = fx[(fx["Gameweek"] == gw) & (fx["team_h"] == team_id)]
            if len(rnd):
                val = rnd.iloc[0]["team_a_difficulty"]
                df.at[idx, "Opponent Difficulty"] = val
                filled_from_fixtures += 1
                if len(preview_filled) < 10:
                    preview_filled.append((idx, gw, "home", val))
                continue
        else:
            rnd = fx[(fx["Gameweek"] == gw) & (fx["team_a"] == team_id)]
            if len(rnd):
                val = rnd.iloc[0]["team_h_difficulty"]
                df.at[idx, "Opponent Difficulty"] = val
                filled_from_fixtures += 1
                if len(preview_filled) < 10:
                    preview_filled.append((idx, gw, "away", val))
                continue

    # Fallback fill with difficulty = 3
    remaining_missing_before = df["Opponent Difficulty"].isna().sum()
    
    df["Opponent Difficulty"] = df["Opponent Difficulty"].fillna(3)

    remaining_missing_after = df["Opponent Difficulty"].isna().sum()

    fallback_filled = remaining_missing_before - remaining_missing_after

    # LOG RESULTS
    print("\n=== FILL SUMMARY ===")
    print(f"Filled from fixtures       : {filled_from_fixtures}")
    print(f"Filled via fallback (=3)   : {fallback_filled}")
    print(f"Total filled               : {filled_from_fixtures + fallback_filled}")
    print(f"Original missing count     : {total_missing}")

    print("\nSample of first filled rows:")
    for sample in preview_filled:
        idx, gw, loc, val = sample
        print(f"  Row {idx} | GW {gw} | {loc} | Difficulty = {val}")

    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    print("\nDone. Saved corrected file.")


if __name__ == "__main__":
    main()

