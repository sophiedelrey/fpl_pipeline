import pandas as pd
import numpy as np
from pathlib import Path

# --- CONFIGURATION ---
OUTPUT_DIR = Path("output")
TRAINING_FILE = OUTPUT_DIR / "training_data.csv"

def diagnose_inconsistencies(file_path: Path):
    """
    Detects and reports inconsistencies in the training dataset,
    where a player appears more than once in the same Gameweek.
    """
    print("=" * 70)
    print(" 🛠️  DIAGNOSING INCONSISTENCIES IN TRAINING DATASET")
    print("=" * 70)

    if not file_path.exists():
        print(f"❌ ERROR: File not found: {file_path}")
        return

    try:
        # 1. Load Data
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        print(f"✅ Loaded {len(df):,} rows from {file_path.name}")
        
        # Check for critical columns
        required_cols = ['Player UUID', 'season', 'Gameweek']
        if not all(col in df.columns for col in required_cols):
            print(f"❌ ERROR: Missing critical identity columns: {required_cols}")
            return
            
        # 2. Grouping and finding duplicates
        # The key is the combination of Player UUID (identity), season, and Gameweek
        duplicates = df.groupby(required_cols).size().reset_index(name='count')
        inconsistencies = duplicates[duplicates['count'] > 1].sort_values('count', ascending=False)
        
        print("\n" + "=" * 70)
        
        if inconsistencies.empty:
            print("🎉 SUCCESS: No inconsistencies (duplicate entries per player-Gameweek) found.")
            print("   The training dataset is consistent regarding player identity.")
            print("=" * 70)
            return

        # 3. Reporting Inconsistencies
        total_inconsistent_groups = len(inconsistencies)
        total_max = inconsistencies['count'].max()
        
        print(f"⚠️  WARNING: Inconsistencies detected!")
        print(f"   Total problematic combinations (Player, Season, GW): {total_inconsistent_groups}")
        print(f"   Maximum entries found for one player in 1 GW: {total_max}")
        print("-" * 70)
        
        # 4. Displaying Examples
        
        # Get a sample of the 5 most frequent issues
        sample_inconsistencies = inconsistencies.head(5)
        
        for idx, row in sample_inconsistencies.iterrows():
            player_uuid = row['Player UUID']
            season = row['season']
            gw = row['Gameweek']
            count = row['count']
            
            # Find the original rows in the DataFrame
            matching_rows = df[(df['Player UUID'] == player_uuid) & 
                             (df['season'] == season) & 
                             (df['Gameweek'] == gw)]
            
            player_name = matching_rows['Player Name'].iloc[0] if 'Player Name' in matching_rows.columns else 'N/A'
            
            print(f"\n   🔴 Inconsistency #{idx + 1} (Count: {count})")
            print(f"   Player: {player_name}")
            print(f"   Season / GW: {season} / {gw}")
            
            # Display critical columns for diagnosis
            display_cols = ['Player Team Name', 'Minutes Played', 'Total Points', 'Opponent Name']
            available_cols = [c for c in display_cols if c in matching_rows.columns]
            
            print(f"   Details of the {count} entries:")
            print(matching_rows[available_cols].to_string(index=False))


    except Exception as e:
        print(f"❌ Unexpected error during loading/processing: {e}")
        
    print("\n" + "=" * 70)


if __name__ == "__main__":
    diagnose_inconsistencies(TRAINING_FILE)