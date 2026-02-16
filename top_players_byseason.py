import pandas as pd
from pathlib import Path

# ========= CONFIG =========
DATA_PATH = Path("output/training_data.csv")
REPORT_DIR = Path("output/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ========= LOAD DATA =========
print("📂 Loading training_data.csv ...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"   → Loaded {len(df):,} rows and {len(df.columns)} columns")

required_cols = ["Player Name", "Player Team Name", "season", "Total Points"]
missing = set(required_cols) - set(df.columns)
if missing:
    raise ValueError(f"❌ Missing required columns: {missing}")

# ========= TOTAL POINTS PER PLAYER PER SEASON =========
print("\n📊 Calculating total points per player and season ...")
group_cols = ["Player Name", "Player Team Name", "season"]

# Αν υπάρχει Web Name, πρόσθεσέ το στα group-by columns
if "Web Name" in df.columns:
    group_cols.insert(1, "Web Name")

player_points = (
    df.groupby(group_cols, dropna=False)["Total Points"]
      .sum()
      .reset_index()
      .rename(columns={"Total Points": "Player_Season_Points"})
)
print(f"   → Found {len(player_points):,} unique player-season combinations")

# ========= QUANTILES PER SEASON =========
print("\n📈 Computing quantile thresholds per season (75% & 90%) ...")
quantiles_by_season = (
    df.groupby("season")["Total Points"]
      .quantile([0.75, 0.9])
      .unstack()
      .rename(columns={0.75: "q75", 0.9: "q90"})
)
print(quantiles_by_season)

# ========= MERGE & FLAG TOP PERFORMERS =========
print("\n🏆 Identifying top performers ...")
top_players = player_points.merge(
    quantiles_by_season, left_on="season", right_index=True
)

# Flag για Top 25% & Top 10%
top_players["Top_25pct"] = top_players["Player_Season_Points"] > top_players["q75"]
top_players["Top_10pct"] = top_players["Player_Season_Points"] > top_players["q90"]

# ========= SAVE TOP 10% (ELITE) =========
elite_players = top_players[top_players["Top_10pct"]].copy()
elite_players = elite_players.sort_values(
    ["season", "Player_Season_Points"], ascending=[True, False]
)

# Αφαίρεσε τη στήλη Top_25pct πριν την αποθήκευση
if "Top_25pct" in elite_players.columns:
    elite_players = elite_players.drop(columns=["Top_25pct"])

elite_path = REPORT_DIR / "top_players_by_season.csv"
elite_players.to_csv(elite_path, index=False, encoding="utf-8-sig")
print(f"✅ Saved top 10% players by season → {elite_path}")

# ========= SAVE TOP 25% (GOOD, NOT ELITE) =========
top25_only = top_players[
    (top_players["Top_25pct"]) & (~top_players["Top_10pct"])
].copy()
top25_only = top25_only.sort_values(
    ["season", "Player_Season_Points"], ascending=[True, False]
)

# Αφαίρεσε τη στήλη Top_10pct πριν την αποθήκευση
if "Top_10pct" in top25_only.columns:
    top25_only = top25_only.drop(columns=["Top_10pct"])

top25_path = REPORT_DIR / "top25_players_by_season.csv"
top25_only.to_csv(top25_path, index=False, encoding="utf-8-sig")
print(f"✅ Saved top 25% (non-elite) players by season → {top25_path}")

# ========= SUMMARY PER SEASON =========
summary = (
    pd.concat([
        elite_players.assign(Category="Top 10%"),
        top25_only.assign(Category="Top 25%"),
    ])
    .groupby(["season", "Category"])["Player Name"]
    .count()
    .unstack(fill_value=0)
)
summary_path = REPORT_DIR / "top_players_summary.csv"
summary.to_csv(summary_path, encoding="utf-8-sig")
print(f"✅ Saved summary of top players per season → {summary_path}")

print("\n🎉 Done! You can now explore the results in 'output/reports/'")



