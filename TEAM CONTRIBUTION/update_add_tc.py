import pandas as pd
from pathlib import Path
import numpy as np

# Causal: uses cumulative values up to GW-1 (shifted)
# No leakage: previous-season stats are historical and available at GW1

# === CONFIGURATION ===
DATA_PATH = Path("output/training_data.csv")
BACKUP_PATH = Path("output/training_data_backup_before_team_contrib.csv")

print("📂 Loading training_data.csv ...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"   → Loaded {len(df):,} rows and {len(df.columns)} columns")

# === BASIC CHECK ===
player_id_col = "Player UUID"
if player_id_col not in df.columns:
    raise KeyError(f"Missing required column '{player_id_col}' in dataset!")

# === CLEANUP: remove any old / duplicate columns ===
old_columns = [
    # team totals
    "Team_Total_Points", "Team_Total_Points_GW", "Team_Total_Points_CUMULATIVE",
    "Team_Total_Points_Causal", "Team_Total_Points_Causal_x", "Team_Total_Points_Causal_y",
    "Team_Total_Points_Season",
    # player totals
    "Player_Season_Points", "Player_Total_Points_Season",
    # contributions
    "Team_Points_Contribution_GW", "Team_Points_Contribution_Causal",
    "Team_Points_Contribution_Season",
    "Team_Points_Contribution_Pct", "Team_Points_Contribution_GW_Pct",
    # ranks
    "Team_Contribution_Rank_GW", "Team_Contribution_Rank_Causal", "Team_Contribution_Rank_Season",
    # leftovers
    "Avg_Contribution_Prev_Season", "Avg_Contribution_Prev_Season_RAW"
]
df = df.drop(columns=[c for c in df.columns if any(x in c for x in old_columns)], errors="ignore")

# remove any lingering duplicate columns (_x / _y patterns)
df = df.loc[:, ~df.columns.duplicated()]

print(f"🧹 Cleanup complete → {len(df.columns)} columns remain")

# === BACKUP ===
print(f"\n💾 Creating backup at {BACKUP_PATH} ...")
df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
print("   ✅ Backup saved.")

# Sort
df = df.sort_values(by=["Player Team Name", "season", "Gameweek", player_id_col]).reset_index(drop=True)

# =========================================================================
# STEP 1 — Team total points (per-GW & cumulative causal)
# =========================================================================
print("\n📊 Calculating team totals (GW & causal)...")

team_points = (
    df.groupby(["Player Team Name", "season", "Gameweek"])["Total Points"]
      .sum()
      .reset_index()
      .rename(columns={"Total Points": "Team_Total_Points_GW"})
)

team_points["Team_Total_Points_CUMULATIVE"] = (
    team_points.groupby(["Player Team Name", "season"])["Team_Total_Points_GW"].cumsum()
)

team_points["Team_Total_Points_Causal"] = (
    team_points.groupby(["Player Team Name", "season"])["Team_Total_Points_CUMULATIVE"].shift(1)
)

df = df.merge(
    team_points[["Player Team Name", "season", "Gameweek",
                 "Team_Total_Points_GW", "Team_Total_Points_Causal"]],
    on=["Player Team Name", "season", "Gameweek"],
    how="left"
)

df["Team_Total_Points_GW"] = df["Team_Total_Points_GW"].fillna(0)
df["Team_Total_Points"] = df["Team_Total_Points_Causal"].fillna(0)

print("   ✅ Created Team_Total_Points_GW & Team_Total_Points (causal).")

# =========================================================================
# STEP 2 — Player cumulative points (causal)
# =========================================================================
df["Player_Season_Points"] = (
    df.groupby([player_id_col, "season"])["Total Points"].cumsum().shift(1).fillna(0)
)
print("   ✅ Player_Season_Points ready.")

# =========================================================================
# STEP 3 — Team Points Contribution (per-GW & causal)
# =========================================================================
df["Team_Points_Contribution_GW"] = np.where(
    df["Team_Total_Points_GW"] > 0,
    df["Total Points"] / df["Team_Total_Points_GW"],
    0
).round(5)

df["Team_Points_Contribution_Causal"] = np.where(
    df["Team_Total_Points"] > 0,
    df["Player_Season_Points"] / df["Team_Total_Points"],
    0
).round(5)

# =========================================================================
# STEP 4 — Handle first 3 GWs (previous season avg)
# =========================================================================
player_avg_prev = (
    df.groupby([player_id_col, "season"])["Team_Points_Contribution_Causal"]
      .mean()
      .reset_index()
      .rename(columns={"Team_Points_Contribution_Causal": "Avg_Contribution_Prev_Season_RAW"})
)
player_avg_prev["season"] = player_avg_prev["season"].apply(
    lambda x: f"{int(x.split('-')[0]) + 1}-{int(x.split('-')[1]) + 1}"
)
df = df.merge(player_avg_prev, on=[player_id_col, "season"], how="left")
df["Avg_Contribution_Prev_Season"] = df["Avg_Contribution_Prev_Season_RAW"].fillna(0)

mask_gw13 = df["Gameweek"].isin([1, 2, 3])
mask_zero = df["Team_Points_Contribution_Causal"] == 0
df.loc[mask_gw13 & mask_zero, "Team_Points_Contribution_Causal"] = (
    df.loc[mask_gw13 & mask_zero, "Avg_Contribution_Prev_Season"]
)

# =========================================================================
# STEP 5 — Ranks (GW & causal)
# =========================================================================
df["Team_Contribution_Rank_GW"] = (
    df.groupby(["Player Team Name", "season", "Gameweek"])["Team_Points_Contribution_GW"]
      .rank(method="min", ascending=False, pct=True)
).round(4)

df["Team_Contribution_Rank_Causal"] = (
    df.groupby(["Player Team Name", "season", "Gameweek"])["Team_Points_Contribution_Causal"]
      .rank(method="min", ascending=False, pct=True)
).round(4)

# =========================================================================
# STEP 6 — Readable percentages
# =========================================================================
for col in ["Team_Points_Contribution_GW", "Team_Points_Contribution_Causal"]:
    df[col + "_Pct"] = (df[col] * 100).round(2)

# =========================================================================
# STEP 7 — Final cleanup before saving
# =========================================================================
df = df.drop(columns=[
    "Avg_Contribution_Prev_Season", "Avg_Contribution_Prev_Season_RAW",
    "Team_Total_Points_CUMULATIVE", "Team_Total_Points_Causal"
], errors="ignore")

# =========================================================================
# STEP 8 — Save & preview
# =========================================================================
print("\n💾 Saving ML-safe dataset (clean, no leakage)...")
df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
print("✅ Saved successfully.")

preview_cols = [
    "Player Name", "Player Team Name", "season", "Gameweek",
    "Total Points", "Team_Total_Points_GW", "Team_Total_Points",
    "Player_Season_Points",
    "Team_Points_Contribution_GW", "Team_Points_Contribution_Causal",
    "Team_Contribution_Rank_GW", "Team_Contribution_Rank_Causal"
]
print("\n📊 Preview (GW 1–5):")
print(df[df["Gameweek"].isin([1, 2, 3, 4, 5])].head(15)[preview_cols].to_string(index=False))

print("\n🎉 Final ML-safe, fully cleaned dataset created — no duplicates, no Season leakage!\n")



