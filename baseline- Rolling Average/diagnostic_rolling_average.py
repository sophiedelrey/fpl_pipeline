import pandas as pd
from pathlib import Path

# ===========================================
# BASE DIR = folder of project (fpl_pipeline)
# ===========================================
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent

# ===========================================
# CORRECT PATHS BASED ON YOUR ACTUAL FOLDERS
# ===========================================
TRAIN_PATH = BASE_DIR / "output" / "training_data.csv"

# ⭐ REAL FILE IN YOUR OUTPUT:
# output/baseline-rolling_average_model/rolling_avg_predictions.csv
PRED_PATH = BASE_DIR / "output" / "baseline-rolling_average_model" / "rolling_avg_predictions.csv"

PLAYER_NAME = "Erling Haaland"
SEASON = "2024-25"
ROLLING_WINDOW = 5

# ===========================================
# LOAD FILES
# ===========================================
print(f"Loading training_data.csv from: {TRAIN_PATH}")
train = pd.read_csv(TRAIN_PATH, encoding="utf-8-sig")

print(f"Loading rolling_avg_predictions.csv from: {PRED_PATH}")
pred = pd.read_csv(PRED_PATH, encoding="utf-8-sig")

# Auto-detect ordering column
order_col = None
for c in ["Gameweek", "GW", "Round", "Fixture"]:
    if c in train.columns:
        order_col = c
        break

if order_col is None:
    raise ValueError("Gameweek column not found in training_data.csv!")

# ===========================================
# FILTER PLAYER + SEASON
# ===========================================
t = train[(train["Player Name"] == PLAYER_NAME) & (train["season"] == SEASON)].copy()
p = pred[(pred["Player Name"] == PLAYER_NAME) & (pred["season"] == SEASON)].copy()

if t.empty:
    print(f"No rows found in training_data for {PLAYER_NAME} {SEASON}")
    exit()

if p.empty:
    print(f"No predictions found for {PLAYER_NAME} {SEASON}")
    exit()

t = t.sort_values(order_col).reset_index(drop=True)
p = p.sort_values("Gameweek").reset_index(drop=True)

print(f"\n=== VERIFY ROLLING AVERAGE FOR {PLAYER_NAME} ({SEASON}) ===\n")

# ===========================================
# VERIFY EACH PREDICTION
# ===========================================
for idx, row in p.iterrows():
    gw = row["Gameweek"]

    if gw not in t[order_col].values:
        continue

    i = t.index[t[order_col] == gw][0]

    start_idx = max(0, i - ROLLING_WINDOW)
    window = t.iloc[start_idx:i]["Total Points"].tolist()

    if len(window) == 0:
        continue

    expected_pred = round(sum(window) / len(window), 3)
    model_pred = round(row["Total Points_Pred"], 3)

    print("---------------------------------------------")
    print(f"GW: {gw}")
    print(f"Rolling window (previous {len(window)} values): {window}")
    print(f"Expected rolling avg: {expected_pred}")
    print(f"Model prediction:     {model_pred}")

    if expected_pred == model_pred:
        print("✔ MATCH — correct rolling average")
    else:
        print("❌ MISMATCH — something is wrong")

print("\n=== END OF DIAGNOSTIC ===\n")

