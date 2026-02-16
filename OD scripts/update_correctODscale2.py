import pandas as pd
import numpy as np
from pathlib import Path

# --- Διαδρομές Αρχείων ---
OUTPUT_DIR = Path("output")
TRAINING_FILE = OUTPUT_DIR / "training_data.csv"
DATA_ROOT = Path("data")
# 🆕 ΝΕΑ: Όνομα αρχείου εξόδου
OUTPUT_REPORT_FILE = OUTPUT_DIR / "opponent_difficulty_check_report.csv"

# --- Σύγκριση (FPL Standard: 1=Easy, 5=Hard) ---
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5

def check_difficulty_scale(df: pd.DataFrame):
    """
    Ελέγχει την κλίμακα Opponent Difficulty ανά σεζόν,
    βρίσκει την πηγή δεδομένων, αναλύει την κατανομή και αποθηκεύει το report.
    """
    print("=" * 70)
    print("🔎 ΕΛΕΓΧΟΣ OPPONENT DIFFICULTY (1=Εύκολο, 5=Δύσκολο)")
    print("=" * 70)

    if not TRAINING_FILE.exists():
        print(f"Το αρχείο training_data.csv δεν βρέθηκε στη διαδρομή: {TRAINING_FILE}")
        return

    df = pd.read_csv(TRAINING_FILE)
    print(f"Φορτώθηκαν {len(df):,} γραμμές από το training_data.csv")

    all_seasons = sorted(df['season'].dropna().unique())

    if len(all_seasons) == 0:
        print("Δεν βρέθηκαν δεδομένα σεζόν.")
        return

    print(f"\nΣύνολο Σεζόν για Έλεγχο: {all_seasons}\n")

    results = []

    for season in all_seasons:
        df_season = df[df['season'] == season].copy()
        total_rows = len(df_season)
        
        # 1. Εντοπισμός Πηγής (βάσει της λογικής του pipeline)
        if season == "2025-26":
            source = f"FPL API (Live) μέσω: {DATA_ROOT / season / 'fixtures.csv'}"
        elif season in ["2018-19", "2019-20"]:
            source = f"Specific Script ({season}) / Εμπλουτισμός από: {DATA_ROOT / season / 'fixtures.csv'}"
        else:
            source = f"Main Notebook Pipeline / Φόρτωση από: {DATA_ROOT / season / 'fixtures.csv'}"
        
        # 2. Ανάλυση Difficulty
        diff_col = 'Opponent Difficulty'
        
        if diff_col not in df_season.columns:
            mean_diff = "N/A (Column Missing)"
            filled_pct = 0
            is_valid = False
            min_val, max_val = "N/A", "N/A"
        else:
            df_season[diff_col] = pd.to_numeric(df_season[diff_col], errors='coerce')
            
            filled_count = df_season[diff_col].notna().sum()
            filled_pct = (filled_count / total_rows) * 100 if total_rows > 0 else 0
            
            non_na_data = df_season[diff_col].dropna()
            
            if len(non_na_data) > 0:
                mean_diff = non_na_data.mean()
                min_val = non_na_data.min()
                max_val = non_na_data.max()
                
                is_valid = (min_val >= MIN_DIFFICULTY) and (max_val <= MAX_DIFFICULTY)
                
            else:
                mean_diff = np.nan
                is_valid = False
                min_val, max_val = np.nan, np.nan
        
        # 3. Εξαγωγή Συμπερασμάτων
        if is_valid and (pd.notna(mean_diff) and mean_diff >= 2.5 and mean_diff <= 3.5):
            scale_status = "1=Εύκολο, 5=Δύσκολο"
        elif is_valid:
            scale_status = "ΕΝΤΟΣ ΟΡΙΩΝ (1-5) - Έλεγχος Κατανομής απαιτείται."
        elif filled_pct == 0:
            scale_status = "ΔΕΝ ΕΧΕΙ ΣΥΜΠΛΗΡΩΘΕΙ (ή στήλη λείπει)"
        else:
            scale_status = "ΛΑΘΟΣ ΟΡΙΑ (Εκτός [1, 5]) ή Αντιστροφή"

        results.append({
            "Season": season,
            "Source File": str(source),
            "Total Rows": total_rows,
            "% Filled": round(filled_pct, 1),
            "Min Difficulty": min_val,
            "Max Difficulty": max_val,
            "Mean Difficulty": round(mean_diff, 2) if pd.notna(mean_diff) else 'N/A',
            "Scale Status": scale_status
        })

    # 4. Αποθήκευση Αποτελεσμάτων
    results_df = pd.DataFrame(results)
    
    try:
        results_df.to_csv(OUTPUT_REPORT_FILE, index=False, encoding='utf-8-sig')
        print("\n" + "=" * 70)
        print(f"🎉 Η ΑΝΑΦΟΡΑ ΑΠΟΘΗΚΕΥΤΗΚΕ: {OUTPUT_REPORT_FILE}")
        print("Μπορείτε να στείλετε αυτό το αρχείο στον καθηγητή σας.")
        print("=" * 70)
    except Exception as e:
        print(f"\n❌ ΑΠΟΤΥΧΙΑ ΑΠΟΘΗΚΕΥΣΗΣ: Δεν ήταν δυνατή η αποθήκευση του report. Λόγος: {e}")

    # Εκτύπωση για έλεγχο
    print("\nΕλέγξτε τα αποτελέσματα που αποθηκεύτηκαν:")
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(results_df.to_string(index=False))


# --- Εκτέλεση ---
if __name__ == "__main__":
    check_difficulty_scale(pd.DataFrame())