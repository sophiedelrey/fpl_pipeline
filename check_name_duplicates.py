import pandas as pd
import os

# --- Configuration ---
DATA_FILE = "output/training_data.csv"

def check_name_duplicates(filepath):
    """
    Checks for duplicate entries based on the key: (Player Name, season, Gameweek).
    
    This is important for finding potential issues where two different players 
    have the same name, or where the aggregation step failed to merge a single 
    player's fragmented records.
    """
    if not os.path.exists(filepath):
        print(f"Error: Data file not found at {filepath}")
        return

    print(f"Loading data from {filepath}...")
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Define the unique key based on the professor's suggestion (Player Name) 
    # combined with the time-series identifiers (season and Gameweek).
    key_cols = ['Player Name', 'season', 'Gameweek']

    # Find rows that are duplicates based on this key (keep all instances)
    # The 'keep=False' ensures we see *all* rows involved in the duplication.
    duplicate_rows = df[df.duplicated(subset=key_cols, keep=False)]

    if duplicate_rows.empty:
        print("\n=======================================================")
        print("SUCCESS: No duplicates found when using the combination:")
        print(f"   {key_cols}")
        print("=======================================================")
    else:
        num_duplicates = len(duplicate_rows)
        print("\n=======================================================")
        print(f"WARNING: Found {num_duplicates} rows involved in duplication!")
        print("These likely represent two different players with the same name,")
        print("or a severe data parsing error.")
        print("=======================================================")
        
        # Display the unique problematic names
        problematic_names = duplicate_rows['Player Name'].unique()
        print("\nProblematic Player Names:")
        for name in problematic_names:
            print(f" - {name}")
        
        # Now, print a detailed example for one of the problematic names
        first_problem_name = problematic_names[0]
        example_df = duplicate_rows[duplicate_rows['Player Name'] == first_problem_name].sort_values(by=['season', 'Gameweek'])
        
        print(f"\nDetailed Example for '{first_problem_name}':")
        # Select key columns for easy inspection
        display_cols = ['Player Name', 'Code', 'Player Team Name', 'season', 'Gameweek', 'Minutes Played', 'Total Points']
        print(example_df[display_cols].head(20).to_markdown(index=False))
        
        # Check if the FPL 'Code' is different (which means two different players)
        unique_codes = example_df['Code'].unique()
        if len(unique_codes) > 1:
            print(f"\nCRITICAL FINDING: Player '{first_problem_name}' has been assigned multiple FPL 'Code' values ({unique_codes}).")
            print("This confirms that *two different players* have the exact same name in the FPL data for the same Gameweek/Season.")
        else:
            print("\nNote: The issue is likely a data fragmentation error that needs further investigation.")

if __name__ == "__main__":
    check_name_duplicates(DATA_FILE)