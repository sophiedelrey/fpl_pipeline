import pandas as pd
import os
import shutil
import datetime
from pathlib import Path

DATA_PATH = Path("output/training_data.csv")
DATA_ROOT = Path("data")
BACKUP_DIR = Path("output")

print("\n==============================================")
print("🔧 REBUILD POSITIONS FROM RAW DATA")
print("==============================================\n")

# 1. Load training dataset
df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
print(f"📥 Loaded training_data.csv with {len(df):,} rows")

# 2. Backup
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = BACKUP_DIR / f"training_data_backup_before_rebuild_positions_{ts}.csv"
shutil.copyfile(DATA_PATH, backup_file)
print(f"💾 Backup created at: {backup_file}\n")

# 3. Load all raw player data (players_raw.csv OR player_idlist.csv)
print("📥 Loading raw player position info from all seasons...\n")

raw_list = []

for season in os.listdir(DATA_ROOT):
    season_path = DATA_ROOT / season
    if not season_path.is_dir():
        continue

    raw_file = season_path / "players_raw.csv"
    alt_file = season_path / "player_idlist.csv"

    df_raw = None

    if raw_file.exists():
        df_raw = pd.read_csv(raw_file, encoding="utf-8-sig")
    elif alt_file.exists():
        df_raw = pd.read_csv(alt_file, encoding="utf-8-sig")
    else:
        print(f"⚠️  No player list found for season {season}")
        continue

    # Normalize column names
    if "element" not in df_raw.columns:
        if "id" in df_raw.columns:
            df_raw.rename(columns={"id": "element"}, inplace=True)
        elif "Code" in df_raw.columns:
            df_raw.rename(columns={"Code": "element"}, inplace=True)

    # We need element and element_type
    if "element" in df_raw.columns and "element_type" in df_raw.columns:
        raw_list.append(df_raw[["element", "element_type"]])
        print(f"  ✔ Season {season}: loaded {len(df_raw)} players")
    else:
        print(f"  ⚠️ Missing element_type in season {season}")

# Combine all seasons
raw_positions = pd.concat(raw_list, ignore_index=True).drop_duplicates("element")

print(f"\n👉 Total unique players with known positions: {len(raw_positions)}")

# 4. Convert numeric position → text label
def convert_position(num):
    mapping = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    try:
        return mapping[int(num)]
    except:
        return None

raw_positions["Position"] = raw_positions["element_type"].map(convert_position)

# 5. Prepare merge
raw_positions.rename(columns={"element": "Code"}, inplace=True)
raw_positions["Code"] = pd.to_numeric(raw_positions["Code"], errors="coerce").astype("Int64")
df["Code"] = pd.to_numeric(df["Code"], errors="coerce").astype("Int64")

# 6. Merge into training dataset
print("\n🔄 Merging positions into training dataset...")
df = df.drop(columns=["Position"], errors="ignore")   # remove broken column
df = df.merge(raw_positions[["Code", "Position"]], on="Code", how="left")

# 7. Report missing
missing_after = df["Position"].isna().sum()
print(f"\n➡️ Missing positions AFTER rebuild: {missing_after:,}")

# 8. Save final file
df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
print("\n💾 Saved fixed training_data.csv!")

print("\n==============================================")
if missing_after == 0:
    print("🎉 SUCCESS — Position fully rebuilt from raw data!")
else:
    print("⚠️ WARNING — Some positions still missing. Check raw data.")
print("==============================================\n")

