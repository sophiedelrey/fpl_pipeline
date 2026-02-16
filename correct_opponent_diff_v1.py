import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path("output/training_data.csv")
BACKUP_PATH = Path("output/training_data_backup_before_correct_OD.csv")

print("📂 Loading dataset...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

# Backup
print("💾 Creating backup...")
df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
print(f"✔ Backup saved at {BACKUP_PATH}")

# Load fixtures for all seasons
fixtures = {}

print("\n📥 Loading fixtures for all seasons...")
for season in df["season"].unique():
    fx_path = Path(f"data/{season}/fixtures.csv")
    if not fx_path.exists():
        print(f"  ⚠ No fixtures for season {season}")
        continue
    
    fx = pd.read_csv(fx_path)
    
    # Standardize
    if "event" in fx.columns:
        fx["Gameweek"] = fx["event"]
    
    fx["team_h"] = pd.to_numeric(fx["team_h"], errors="coerce")
    fx["team_a"] = pd.to_numeric(fx["team_a"], errors="coerce")
    fx["team_h_difficulty"] = pd.to_numeric(fx["team_h_difficulty"], errors="coerce")
    fx["team_a_difficulty"] = pd.to_numeric(fx["team_a_difficulty"], errors="coerce")
    fx["Gameweek"] = pd.to_numeric(fx["Gameweek"], errors="coerce")
    
    fixtures[season] = fx
    print(f"  ✔ Loaded fixtures for season {season}: {len(fx)} rows")

print("\n🔧 Recomputing Opponent Difficulty using CORRECT logic...")

fixed = 0

for idx, row in df.iterrows():
    season = row["season"]
    gw = row["Gameweek"]
    team_id = row["Player Team ID"]
    is_home = row["Is Home"]

    if season not in fixtures:
        continue
    
    fx = fixtures[season]

    if pd.isna(gw) or pd.isna(team_id) or pd.isna(is_home):
        continue

    gw = int(gw)

    if is_home:
        # Player's team is home → opponent is away team
        match = fx[(fx["Gameweek"] == gw) & (fx["team_h"] == team_id)]
        if len(match):
            opponent_id = int(match.iloc[0]["team_a"])
            opponent_diff = match.iloc[0]["team_h_difficulty"]  # DIFFICULTY FOR OPPONENT
        else:
            continue
    else:
        # Player's team is away → opponent is home team
        match = fx[(fx["Gameweek"] == gw) & (fx["team_a"] == team_id)]
        if len(match):
            opponent_id = int(match.iloc[0]["team_h"])
            opponent_diff = match.iloc[0]["team_a_difficulty"]  # DIFFICULTY FOR OPPONENT
        else:
            continue

    df.at[idx, "Opponent Difficulty"] = opponent_diff
    df.at[idx, "Opponent ID"] = opponent_id
    fixed += 1

print(f"\n✔ Fixed Opponent Difficulty for {fixed} rows.")

# -------------------------
# Verification Test:
# Arsenal vs Luton
# -------------------------

print("\n🔍 Verification test: Arsenal vs Luton (any season)")
test_rows = df[
    (df["Player Team Name"] == "Arsenal") & 
    (df["Opponent Name"].str.contains("Luton", na=False))
][[
    "season", "Gameweek", "Is Home", "Opponent Name", "Opponent Difficulty"
]]

if len(test_rows) == 0:
    print("⚠ No Arsenal vs Luton rows found in dataset.")
else:
    print("\nSample Arsenal vs Luton rows (AFTER FIX):")
    print(test_rows.head(10))

# Save final
df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
print("\n💾 Saved corrected dataset to training_data.csv")
print("🎉 Done. Opponent Difficulty corrected.")
