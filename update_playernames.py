import pandas as pd
import os
from pathlib import Path
import requests
import re
from unidecode import unidecode # Προσθήκη unidecode για συμβατότητα

# === CONFIG ===
DATA_DIR = Path("data")
OUTPUT_FILE = Path("output/training_data.csv")
BACKUP_FILE = Path("output/training_data_backup_before_playernames_fix.csv")
# ΣΗΜΕΙΩΣΗ: Προστέθηκε η σεζόν 2025-26 για να είναι πλήρης η λίστα
SEASONS = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"] 
VAASTAV_BASE = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"

# === STEP 1: Load training data ===
print("📂 Loading training_data.csv ...")
# Χρησιμοποιούμε errors='ignore' για να αποφύγουμε σφάλματα αν ο κώδικας τρέξει εκτός του vaastav_dataset
try:
    df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
    print(f"   → Loaded {len(df):,} rows")
except FileNotFoundError:
    print(f"❌ CRITICAL: {OUTPUT_FILE} not found. Ensure pipeline notebook ran first. Exiting.")
    exit()

# === STEP 2: Backup ===
print(f"💾 Creating backup at {BACKUP_FILE} ...")
df.to_csv(BACKUP_FILE, index=False, encoding='utf-8-sig')
print("   ✅ Backup created")

# === STEP 3: Build name mapping for each season (Διατηρείται ως έχει, δεν χρειάζεται αλλαγή) ===
all_mappings = {}

for season in SEASONS:
    local_path = DATA_DIR / season / "player_idlist.csv"
    if not local_path.exists():
        # Try to download from GitHub
        url = f"{VAASTAV_BASE}/{season}/player_idlist.csv"
        print(f"🌐 Downloading {url} ...")
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(r.content)
                print(f"   ✅ Saved {local_path}")
            else:
                # print(f"   ⚠️  Could not download for {season} (HTTP {r.status_code})")
                continue
        except Exception as e:
            # print(f"   ⚠️  Error downloading for {season}: {e}")
            continue
    
    # Load the CSV
    try:
        pid_df = pd.read_csv(local_path, encoding='utf-8')
        # Handle variations in column names
        cols = [c.lower() for c in pid_df.columns]
        if "first_name" in cols and "second_name" in cols:
            pid_df.columns = cols
            pid_df["full_name"] = pid_df["first_name"].str.strip() + " " + pid_df["second_name"].str.strip()
            mapping = dict(zip(pid_df["web_name"].astype(str).str.lower(), pid_df["full_name"]))
            all_mappings[season] = mapping
            # print(f"   🧩 Built mapping for {season}: {len(mapping)} players")
    except Exception as e:
        # print(f"   ⚠️  Could not read mapping for {season}: {e}")
        pass # Συνεχίζουμε

# === STEP 4: Apply mappings (merge by Code per season; fallback to regex clean) ===
# Χρησιμοποιούμε τη strip_suffixes κυρίως ως fallback καθαρισμό ονόματος (Player Name), όχι για το Player Name Norm
def strip_suffixes(name: str) -> str:
    """Καθαρίζει underscores και ΑΦΑΙΡΕΙ τελικούς αριθμούς (π.χ. '_541' ή ' 541')."""
    if pd.isna(name):
        return name
    s = str(name)
    s = s.replace("_", " ")
    # αφαίρεση τελικών αριθμών με ή χωρίς κενά/underscore πριν
    s = re.sub(r'[\s_]*\d+\s*$', '', s)
    # συμπίεση πολλαπλών κενών
    s = " ".join(s.split()).strip()
    # κεφαλαιοποίηση τύπου ονόματος
    return s.title()

print("\n🧹 Cleaning player names using per-season mapping on Code (element id) ...")

updated_count = 0
changed_examples = {}

# Θα δουλέψουμε ανά season για να κάνουμε merge με το σωστό player_idlist.csv
seasons_in_data = sorted(map(str, df["season"].unique()))
for season in seasons_in_data:
    season_mask = df["season"].astype(str) == season
    if not season_mask.any():
        continue

    mapping = None
    pid_path = DATA_DIR / season / "player_idlist.csv"
    if pid_path.exists():
        try:
            pid_df = pd.read_csv(pid_path, encoding="utf-8")
            # ομογενοποίηση ονομάτων στηλών
            pid_df.columns = [c.lower() for c in pid_df.columns]
            # περιμένουμε first_name, second_name, web_name, id
            if {"first_name","second_name","web_name","id"} <= set(pid_df.columns):
                pid_df["full_name"] = (pid_df["first_name"].astype(str).str.strip() 
                                     + " " 
                                     + pid_df["second_name"].astype(str).str.strip())
                # id εδώ είναι το FPL element id -> ταιριάζει με "Code" στο training_data
                mapping = pid_df[["id","full_name","web_name"]].copy()
                mapping.rename(columns={"id":"Code"}, inplace=True)
                # τύπος για ασφάλεια
                mapping["Code"] = pd.to_numeric(mapping["Code"], errors="coerce").astype("Int64")
        except Exception as e:
            print(f"   ⚠️  Failed to read mapping for {season}: {e}")

    # Αν έχουμε έγκυρο mapping, κάνε merge
    if mapping is not None and not mapping.empty:
        sub = df.loc[season_mask, ["Code", "Player Name"]].copy() # Παίρνουμε μόνο Code και Player Name
        sub["Code"] = pd.to_numeric(sub["Code"], errors="coerce").astype("Int64")
        
        sub = sub.merge(mapping, on="Code", how="left", suffixes=("",""))
        
        before_names = sub["Player Name"].copy()
        has_full = sub["full_name"].notna()

        # 1. Ενημέρωσε μόνο το Player Name με το full_name
        sub.loc[has_full, "Player Name"] = sub.loc[has_full, "full_name"]
        
        # 2. Χρησιμοποίησε strip_suffixes για όσους δεν βρέθηκαν
        sub.loc[~has_full, "Player Name"] = sub.loc[~has_full, "Player Name"].apply(strip_suffixes)

        # ❌ ΑΦΑΙΡΕΘΗΚΕ: sub["Player Name Norm"] = sub["Player Name"].str.lower()
        
        # στατιστικά αλλαγών
        diffs = before_names != sub["Player Name"]
        for old, new in zip(before_names[diffs], sub.loc[diffs, "Player Name"]):
            if old not in changed_examples:
                changed_examples[old] = new
        updated_count += diffs.sum()

        # 3. Γράψε πίσω ΜΟΝΟ το Player Name (το Player Name Norm μένει ανέπαφο)
        df.loc[season_mask, "Player Name"] = sub["Player Name"].values
    else:
        # Δεν έχουμε mapping: καθάρισε με regex όλα τα ονόματα αυτής της season
        before_names = df.loc[season_mask, "Player Name"].copy()
        df.loc[season_mask, "Player Name"] = df.loc[season_mask, "Player Name"].apply(strip_suffixes)
        
        # ❌ ΑΦΑΙΡΕΘΗΚΕ: df.loc[season_mask, "Player Name Norm"] = df.loc[season_mask, "Player Name"].str.lower()

        diffs = before_names != df.loc[season_mask, "Player Name"]
        for old, new in zip(before_names[diffs], df.loc[season_mask, "Player Name"][diffs]):
            if old not in changed_examples:
                changed_examples[old] = new
        updated_count += diffs.sum()

print(f"✅ Updated {updated_count:,} player names across all seasons (Player Name Norm left untouched).")

# === STEP 5: Save updated data ===
print(f"\n💾 Saving cleaned dataset back to {OUTPUT_FILE} ...")
df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
print("🎉 Player names cleaned successfully!")

# === STEP 6: Consistency check & summary ===
unique_changes = len(changed_examples)
print(f"\n🔍 Consistency Summary:")
print(f"   → Unique player name variants fixed: {unique_changes}")
if unique_changes > 0:
    print("   Examples of cleaned names:")
    for old, new in list(changed_examples.items())[:8]:
        print(f"     - '{old}'  →  '{new}'")
print("✅ Player name normalization complete!\n")

# === STEP 6: Consistency check & summary === (ΔΙΑΓΡΑΦΕΤΑΙ το διπλό block)
# ...
