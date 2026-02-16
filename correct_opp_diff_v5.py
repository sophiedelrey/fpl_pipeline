import pandas as pd
import numpy as np
from pathlib import Path

TRAIN_PATH = Path("output/training_data.csv")
BACKUP_PATH = Path("output/training_data_backup_before_final_OD_fix.csv")
DATA_ROOT = Path("data")

print("Loading training data...")
df = pd.read_csv(TRAIN_PATH, encoding="utf-8-sig")
print(f"Loaded {len(df):,} rows.")

print("Creating backup...")
df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
print(f"Backup saved at {BACKUP_PATH}")

# ----------------------------------------------------------
# Load all fixtures for all seasons
# ----------------------------------------------------------
fixtures = {}

print("Loading fixtures for all seasons...")
for season in df["season"].astype(str).unique():
    fx_path = DATA_ROOT / season / "fixtures.csv"
    if fx_path.exists():
        fx = pd.read_csv(fx_path)
        fx["Gameweek"] = pd.to_numeric(fx["event"], errors="coerce")
        fx["team_h"] = pd.to_numeric(fx["team_h"], errors="coerce")
        fx["team_a"] = pd.to_numeric(fx["team_a"], errors="coerce")
        fx["team_h_difficulty"] = pd.to_numeric(fx["team_h_difficulty"], errors="coerce")
        fx["team_a_difficulty"] = pd.to_numeric(fx["team_a_difficulty"], errors="coerce")
        fixtures[season] = fx
        print(f"  ✔ Loaded fixtures for {season}: {len(fx)} rows")
    else:
        fixtures[season] = None
        print(f"  ❌ No fixtures for {season}")

# ----------------------------------------------------------
# Function to compute OD from fixtures
# ----------------------------------------------------------
def compute_opponent_difficulty(row):
    season = str(row["season"])
    gw = row["Gameweek"]
    team_id = row["Player Team ID"]
    is_home = row["Is Home"]

    if season not in fixtures:
        return np.nan
    fx = fixtures[season]
    if fx is None or pd.isna(gw) or pd.isna(team_id):
        return np.nan

    gw = int(gw)

    # Case 1: Player is HOME
    if is_home:
        m = fx[(fx["Gameweek"] == gw) & (fx["team_h"] == team_id)]
        if len(m) == 1:
            return m.iloc[0]["team_h_difficulty"]

    # Case 2: Player is AWAY
    if not is_home:
        m = fx[(fx["Gameweek"] == gw) & (fx["team_a"] == team_id)]
        if len(m) == 1:
            return m.iloc[0]["team_a_difficulty"]

    return np.nan

# ----------------------------------------------------------
# Recompute Opponent Difficulty for all rows
# ----------------------------------------------------------
print("Recomputing Opponent Difficulty...")
filled = 0
total_nan_before = df["Opponent Difficulty"].isna().sum()

for idx, row in df.iterrows():
    new_val = compute_opponent_difficulty(row)
    if not pd.isna(new_val):
        df.at[idx, "Opponent Difficulty"] = new_val
        filled += 1

total_nan_after = df["Opponent Difficulty"].isna().sum()

print("\n=== FINAL OD FIX SUMMARY ===")
print(f"Rows updated with OD        : {filled}")
print(f"NaN before                  : {total_nan_before}")
print(f"NaN after                   : {total_nan_after}")
print(f"Successfully filled OD rows : {total_nan_before - total_nan_after}")

# ----------------------------------------------------------
# SAVE
# ----------------------------------------------------------
df.to_csv(TRAIN_PATH, index=False, encoding="utf-8-sig")
print("\nSaved updated training_data.csv")
print("Done!")
