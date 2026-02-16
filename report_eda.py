import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import math

# ========= CONFIG =========
DATA_PATH = Path("output/training_data.csv")
REPORT_DIR = Path("output/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ========= LOAD =========
print("📂 Loading training_data.csv ...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"   → Loaded {len(df):,} rows and {len(df.columns)} columns")

# Βρες τη στήλη UUID
if "Player UUID" in df.columns:
    uuid_col = "Player UUID"
elif "player_uuid" in df.columns:
    uuid_col = "player_uuid"
else:
    raise ValueError("❌ Δεν βρέθηκε στήλη με UUID. Πρόσθεσε/ομάλισε την 'Player UUID'.")

# ========= PER-PLAYER POINTS (per season) =========
print("\n📊 Calculating total points per player and season ...")
required_cols = ["Player Name", "Player Team Name", "season", "Total Points", uuid_col]
missing = set(required_cols) - set(df.columns)
if missing:
    raise ValueError(f"❌ Missing required columns: {missing}")

player_points = (
    df.groupby([uuid_col, "Player Name", "Player Team Name", "season"], dropna=False)["Total Points"]
      .sum()
      .reset_index()
      .rename(columns={"Total Points": "Player_Season_Points"})
)
out_csv = REPORT_DIR / "player_points_by_season.csv"
player_points.to_csv(out_csv, index=False, encoding="utf-8-sig")
print(f"✅ Saved per-player points → {out_csv}")

# ========= BASIC EDA =========
print("\n📈 Running basic EDA ...")

# 1) Global describe
desc = df["Total Points"].describe(percentiles=[0.25, 0.5, 0.75])
desc.to_csv(REPORT_DIR / "total_points_describe.csv", header=["value"])
print("✅ Saved describe → total_points_describe.csv")

# 2) Per-season describe
per_season_desc = (
    df.groupby("season")["Total Points"]
      .describe(percentiles=[0.25, 0.5, 0.75])
)
per_season_desc.to_csv(REPORT_DIR / "total_points_describe_by_season.csv")
print("✅ Saved per-season describe → total_points_describe_by_season.csv")

# 3) Quantiles 25/50/75 (global)
quantiles = df["Total Points"].quantile([0.25, 0.5, 0.75]).rename("quantile_value")
quantiles.index = [f"{int(q*100)}%" for q in quantiles.index]
quantiles.to_csv(REPORT_DIR / "total_points_quantiles_25_50_75.csv")
print("✅ Saved quantiles → total_points_quantiles_25_50_75.csv")

# 4) Distribution plots ανά season (αντί για QQ plots)
print("\n📊 Plotting point distributions per season ...")

for seas, dfg in df.groupby("season"):
    if dfg["Total Points"].notna().sum() < 20:
        continue
    plt.figure(figsize=(6, 4))
    plt.hist(dfg["Total Points"].dropna(), bins=25, color="#4C72B0", edgecolor="white", alpha=0.8)
    plt.title(f"Distribution of Total Points — Season {seas}", fontsize=12, fontweight="bold")
    plt.xlabel("Total Points")
    plt.ylabel("Frequency")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    p = REPORT_DIR / f"distribution_total_points_{seas}.png"
    plt.savefig(p, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"✅ Saved → {p}")

# 5) Συνολικό histogram όλων των σεζόν
plt.figure(figsize=(6, 4))
plt.hist(df["Total Points"].dropna(), bins=40, color="#4C72B0", edgecolor="white", alpha=0.8)
plt.title("Distribution of Total Points — All Seasons Combined", fontsize=12, fontweight="bold")
plt.xlabel("Total Points")
plt.ylabel("Frequency")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
p_all = REPORT_DIR / "distribution_total_points_all_seasons.png"
plt.savefig(p_all, bbox_inches="tight", dpi=150)
plt.close()
print(f"✅ Saved overall distribution → {p_all}")

# 6) ΕΝΙΑΙΟ figure με όλα τα seasons (subplots)
print("\n🖼️ Creating combined subplot figure for all seasons ...")

seasons = sorted(df["season"].dropna().unique())
n = len(seasons)
cols = 3
rows = math.ceil(n / cols)

fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 4))
axes = axes.flatten()

for i, seas in enumerate(seasons):
    dfg = df[df["season"] == seas]
    axes[i].hist(dfg["Total Points"].dropna(), bins=25, color="#4C72B0", edgecolor="white", alpha=0.8)
    axes[i].set_title(f"Season {seas}", fontsize=11, fontweight="bold")
    axes[i].set_xlabel("Total Points")
    axes[i].set_ylabel("Frequency")
    axes[i].grid(axis="y", alpha=0.3)

# Αν υπάρχουν λιγότερα subplots από τα slots, κλείσε τα κενά
for j in range(i + 1, len(axes)):
    fig.delaxes(axes[j])

plt.tight_layout()
combined_path = REPORT_DIR / "distributions_all_seasons_subplot.png"
plt.savefig(combined_path, bbox_inches="tight", dpi=150)
plt.close()
print(f"✅ Saved combined subplot figure → {combined_path}")

print("\n🎉 Reports complete! All results saved in 'output/reports/'")


