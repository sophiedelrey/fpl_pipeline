import pandas as pd

df = pd.read_csv("output/training_data.csv", encoding="utf-8-sig")

# Standardize opponent name in case of variants
df["Opponent Name"] = df["Opponent Name"].str.strip().str.lower()

target = "man utd"
target_norm = target.lower().strip()

sub = df[df["Opponent Name"] == target_norm].copy()

print(f"\n🔍 Found {len(sub):,} rows with Opponent Name = '{target}'\n")

# Sort so you can see exactly how OD behaves across the season
sub = sub.sort_values(["season", "Gameweek"])

cols = [
    "season", "Gameweek", 
    "Player Team Name", 
    "Opponent Name", 
    "Opponent Difficulty"
]

# Print rows with highlight for “wrong” difficulty
for _, row in sub[cols].iterrows():
    season = row["season"]
    gw = int(row["Gameweek"])
    pteam = row["Player Team Name"]
    od = int(row["Opponent Difficulty"])
    
    warn = ""
    if od not in [4, 5]:  # Man Utd should always be hard opponent
        warn = "  ⚠️  POSSIBLE ERROR"
    
    print(
        f"{season} | GW{gw:<2} | {pteam:<15} vs Man Utd | OD = {od}{warn}"
    )
