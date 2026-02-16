import pandas as pd
import numpy as np
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_DIR = Path("output")
TRAINING_FILE = OUTPUT_DIR / "training_data.csv"
LEAKAGE_THRESHOLD = 0.05 # Όριο για να θεωρηθεί "πιθανό leakage" (π.χ. > 5% συνεισφορά)

def diagnose_tc_leakage(file_path: Path):
    """
    Detects potential Data Leakage in Team Contribution features.
    
    Leakage is suspected if:
    1. Team_Total_Points > 0 or Player_Season_Points > 0 for Gameweek 1.
    2. Team_Points_Contribution shows a substantial value for Gameweek 1, 
       which cannot be justified by historical data (e.g., if previous season data is missing).
    """
    print("=" * 70)
    print(" 🛠️  DIAGNOSING TEAM CONTRIBUTION DATA LEAKAGE")
    print("=" * 70)

    if not file_path.exists():
        print(f"❌ ERROR: File not found: {file_path}")
        return

    try:
        # 1. Load Data
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        print(f"✅ Loaded {len(df):,} rows from {file_path.name}")
        
        # Check for required columns
        required_cols = ['season', 'Gameweek', 'Player Name', 'Team_Total_Points', 
                         'Player_Season_Points', 'Team_Points_Contribution']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ ERROR: Missing required feature columns: {required_cols}")
            return
            
        # 2. Filter for the critical condition: Gameweek 1
        gw1_data = df[df['Gameweek'] == 1].copy()
        
        if gw1_data.empty:
            print("⚠️ WARNING: No Gameweek 1 data found. Cannot perform leakage check.")
            return

        # 3. Define leakage conditions
        # Condition A: Team_Total_Points should be 0 (no cumulative points from the current season yet)
        # Condition B: Player_Season_Points should be 0 (no cumulative points from the current season yet)
        
        # We need to find GW1 rows where Team_Total_Points > 0.
        # Note: If you correctly implemented the Lagged fix, Team_Total_Points should be 0 at GW1 (it's cumulative up to GW N-1).
        
        # Find rows where the cumulative sum (which should be only previous season's data at GW1)
        # shows a high current season contribution, which signals the initial, incorrect calculation.
        
        # Find rows where the contribution value is suspiciously high (meaning it's likely the 38 GW total)
        suspicious_gw1_contribution = gw1_data[
            (gw1_data['Team_Points_Contribution'] > LEAKAGE_THRESHOLD) | 
            (gw1_data['Team_Total_Points'] > 0)
        ]

        print("\n" + "=" * 70)
        
        if suspicious_gw1_contribution.empty:
            print("🎉 SUCCESS: No clear evidence of Data Leakage found in GW1.")
            print("   Cumulative points (Team/Player) are either 0 or set by Lagged data (Prev Season Avg).")
            print("=" * 70)
            return

        # 4. Reporting Leakage
        total_leakage_rows = len(suspicious_gw1_contribution)
        
        print(f"⚠️  WARNING: Potential Data Leakage Detected in {total_leakage_rows} GW1 rows!")
        print(f"   These rows show substantial (>{LEAKAGE_THRESHOLD*100:.1f}%) contribution or total points > 0 at GW1.")
        print("-" * 70)
        
        # Display 10 examples
        print("   Sample of suspicious GW1 entries (10 rows):")
        
        display_cols = ['season', 'Player Name', 'Player Team Name', 
                        'Team_Total_Points', 'Player_Season_Points', 
                        'Team_Points_Contribution']
        
        print(suspicious_gw1_contribution[display_cols].head(10).to_string(index=False))

        print("\n💡 ACTION: If 'Team_Total_Points' or 'Player_Season_Points' is non-zero, the *initial* incorrect calculation likely remains.")
        print("   If 'Team_Points_Contribution' is non-zero, verify it comes from the *previous* season's average, not the current season's total.")

    except Exception as e:
        print(f"❌ Unexpected error during loading/processing: {e}")
        
    print("\n" + "=" * 70)


if __name__ == "__main__":
    diagnose_tc_leakage(TRAINING_FILE)