import pandas as pd
from pathlib import Path

# Path to your CSV file
CSV_FILE = Path("data/fpl_scout/2024-25/ffs_all_players_gw_2024-25.csv")

# Read the CSV
print(f"Reading {CSV_FILE}...")
df = pd.read_csv(CSV_FILE)

# Show current columns
print(f"\nCurrent columns ({len(df.columns)} total):")
print(df.columns.tolist())

# Check if col_0 exists
if 'col_0' in df.columns:
    print("\n✓ Found 'col_0' column - removing it...")
    df = df.drop(columns=['col_0'])
    
    # Save back to the same file
    df.to_csv(CSV_FILE, index=False)
    print(f"\n✓ Successfully removed 'col_0' and saved to {CSV_FILE}")
    print(f"\nNew columns ({len(df.columns)} total):")
    print(df.columns.tolist())
else:
    print("\n✗ 'col_0' column not found - no changes made")

print(f"\n✓ Total rows in file: {len(df)}")