import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path("output/training_data.csv")
BACKUP = Path("output/training_data_backup_before_full_fix.csv")

print("Loading training dataset...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

print("Creating backup...")
df.to_csv(BACKUP, index=False, encoding="utf-8-sig")

# Collect fixtures from all seasons
fixtures = {}
for season in df["season"].unique():
    fx_path = Path(f"data/{season}/fixtures.csv")
    if fx_path.exists():
        fx = pd.read_csv(fx_path)
        fx["Gameweek"] = fx["event"]
        fx["team_h"] = pd.to_numeric(fx["team_h"])
        fx["team_a"] = pd.to_numeric(fx["team_a"])
        fx["team_h_difficulty"] = pd.to_numeric(fx["team_h_difficulty"])
        fx["team_a_difficulty"] = pd.to_numeric(fx["team_a_difficulty"])
        fixtures[season] = fx

fixed = 0

for idx, row in df.iterrows():
    season = row["season"]
    gw = row["Gameweek"]
    team_id = row["Player Team ID"]
    is_home = row["Is Home"]
    
    fx = fixtures.get(season)
    if fx is None:
        continue
    
    if is_home:
        match = fx[(fx["Gameweek"] == gw) & (fx["team_h"] == team_id)]
        if len(match):
            df.at[idx, "Opponent Difficulty"] = match.iloc[0]["team_a_difficulty"]
            fixed += 1
    else:
        match = fx[(fx["Gameweek"] == gw) & (fx["team_a"] == team_id)]
        if len(match):
            df.at[idx, "Opponent Difficulty"] = match.iloc[0]["team_h_difficulty"]
            fixed += 1

print(f"Fixed {fixed} difficulty entries.")
df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
print("Done! Full rebuild complete.")
