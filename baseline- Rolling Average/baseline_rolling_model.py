import pandas as pd
import numpy as np
from pathlib import Path

# ================================================================
# CONFIG — PORTABLE PATHS BASED ON SCRIPT LOCATION
# ================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

DATA_PATH = BASE_DIR / "output" / "training_data_v6_no0min_trial.csv"

BASELINE_DIR = BASE_DIR / "output" / "baseline-rolling_average_model"
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

PRED_PATH = BASELINE_DIR / "rolling_avg_predictions.csv"
TRAIN_PATH = BASELINE_DIR / "rolling_avg_train.csv"
VALID_PATH = BASELINE_DIR / "rolling_avg_validation.csv"
SPLIT_PATH = BASELINE_DIR / "rolling_avg_split.csv"
MAE_SUMMARY_PATH = BASELINE_DIR / "rolling_avg_MAE_summary.csv"

ROLLING_WINDOW = 5
VAL_LAST_N = 5   # ✔ SAME AS LINEAR REGRESSION

# ================================================================
# LOAD DATA
# ================================================================
print("📂 Loading dataset...")
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
df = df.sort_values(["Player UUID", "season", "Gameweek"]).reset_index(drop=True)

print(f"   → Loaded {len(df):,} rows\n")

# ================================================================
# TARGET = NEXT-GW TOTAL POINTS (MATCHING LINEAR REGRESSION)
# ================================================================
print("🎯 Creating Target_NextGW...")

df["Target_NextGW"] = df.groupby(
    ["Player UUID", "season"]
)["Total Points"].shift(-1)

before = len(df)
df = df.dropna(subset=["Target_NextGW"]).reset_index(drop=True)
after = len(df)

df["Target_NextGW"] = df["Target_NextGW"].astype(float)

print(f"   → Removed {before - after} rows (final GWs of seasons)")
print(f"   → Remaining rows: {len(df):,}\n")

# ================================================================
# CAUSAL ROLLING AVERAGE BASELINE
# ================================================================
print(f"📊 Computing rolling average of last {ROLLING_WINDOW} Total Points...")

df["Baseline_Pred"] = (
    df.groupby(["Player UUID", "season"])["Total Points"]
      .transform(lambda s: s.rolling(ROLLING_WINDOW, min_periods=1).mean())
)

print("✔ Rolling average computed.\n")

# ================================================================
# GLOBAL SPLIT — LAST-5 OBSERVATIONS PER PLAYER
# (IDENTICAL LOGIC TO LINEAR REGRESSION)
# ================================================================
print("📐 Assigning last-5 rows per player to Validation...")

df["Train_or_Validation"] = "Train"

for uuid, g in df.groupby("Player UUID", sort=False):
    last5 = g.tail(VAL_LAST_N).index
    df.loc[last5, "Train_or_Validation"] = "Validation"

print(df["Train_or_Validation"].value_counts())
print("✔ Split applied.\n")

# ================================================================
# (OPTIONAL) DEBUGGING — SEE EXACT LAST 5 FOR EACH PLAYER
# ================================================================
DEBUG = False  # ← change to True to inspect

if DEBUG:
    for uuid, g in df.groupby("Player UUID"):
        print("\nPLAYER:", uuid)
        print("Total rows:", len(g))
        print("Last 5 rows:")
        print(g.tail(5)[["season", "Gameweek", "Total Points", 
                        "Baseline_Pred", "Target_NextGW"]])
    print("\n⚠️ DEBUGGING MODE ENABLED — SCRIPT STOPPED.")
    raise SystemExit

# ================================================================
# BUILD OUTPUT DATAFRAME
# ================================================================
df_out = df.copy()

df_out["Prediction_For_GW"] = df_out["Gameweek"] + 1
df_out["Total_Points_Actual"] = df_out["Target_NextGW"]
df_out["Total_Points_Predicted"] = df_out["Baseline_Pred"].round(4)
df_out["Error"] = (df_out["Total_Points_Actual"] - df_out["Total_Points_Predicted"]).abs().round(4)

keep_cols = [
    "Player UUID", "Player Name", "Web Name",
    "season", "Gameweek", "Prediction_For_GW",
    "Total_Points_Actual", "Total_Points_Predicted",
    "Error", "Train_or_Validation"
]

results = df_out[keep_cols]

# ================================================================
# SAVE OUTPUTS
# ================================================================
print("💾 Saving outputs...")

results.to_csv(PRED_PATH, index=False, encoding="utf-8-sig")
results[results["Train_or_Validation"] == "Train"].to_csv(TRAIN_PATH, index=False, encoding="utf-8-sig")
results[results["Train_or_Validation"] == "Validation"].to_csv(VALID_PATH, index=False, encoding="utf-8-sig")

df[["Player UUID", "season", "Gameweek", "Train_or_Validation"]].to_csv(
    SPLIT_PATH, index=False, encoding="utf-8-sig"
)

print("✔ Saved predictions, train/val splits.\n")

# ================================================================
# METRICS (MAE / RMSE)
# ================================================================
print("📊 Calculating metrics...")

mae_train = results[results["Train_or_Validation"] == "Train"]["Error"].mean()
mae_valid = results[results["Train_or_Validation"] == "Validation"]["Error"].mean()

rmse_train = np.sqrt(np.mean(
    (results[results["Train_or_Validation"] == "Train"]["Total_Points_Actual"]
     - results[results["Train_or_Validation"] == "Train"]["Total_Points_Predicted"]) ** 2
))

rmse_valid = np.sqrt(np.mean(
    (results[results["Train_or_Validation"] == "Validation"]["Total_Points_Actual"]
     - results[results["Train_or_Validation"] == "Validation"]["Total_Points_Predicted"]) ** 2
))

summary = pd.DataFrame({
    "Metric": ["MAE_Train", "MAE_Validation", "RMSE_Train", "RMSE_Validation"],
    "Value": [mae_train, mae_valid, rmse_train, rmse_valid]
})

summary.to_csv(MAE_SUMMARY_PATH, index=False, encoding="utf-8-sig")

print(summary)
print("\n✔ Baseline metrics saved.\n")

# ================================================================
# UPDATE GLOBAL MODEL PERFORMANCE TABLE
# ================================================================
MODEL_PERF = BASE_DIR / "output" / "model_performance" / "Model_Performance.csv"
MODEL_PERF.parent.mkdir(exist_ok=True)

new_row = pd.DataFrame([{
    "Model": "Rolling Average (TotalPoints)",
    "MAE_Train": round(mae_train, 5),
    "MAE_Validation": round(mae_valid, 5),
    "RMSE_Train": round(rmse_train, 5),
    "RMSE_Validation": round(rmse_valid, 5),
    "Relative_Improvement_vs_Baseline": 0.0
}])

if MODEL_PERF.exists():
    old = pd.read_csv(MODEL_PERF)
    old = old[~old["Model"].str.contains("Rolling Average", na=False)]
    final = pd.concat([old, new_row], ignore_index=True)
else:
    final = new_row

final.to_csv(MODEL_PERF, index=False, encoding="utf-8-sig")
print("✔ Updated Model_Performance.csv")

print("\n🎉 BASELINE MODEL COMPLETED — FAIR & MATCHES LINEAR REGRESSION SPLIT")



