# %%  (replace your existing save_player_uuid_mapping function)
def save_player_uuid_mapping(df, player_uuid_map, player_web_names_by_season, output_path=None):
    """
    Αποθηκεύει το mapping παικτών με UUIDs στο ίδιο folder όπου σώζεται και το training_data.csv.
    """
    # Αν δεν έχει δοθεί explicit path, σώσε το mapping δίπλα στο OUTPUT_FILE
    if output_path is None:
        output_dir = os.path.dirname(OUTPUT_FILE)  # π.χ. "output"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "player_uuid_mapping.csv")

    # Δημιουργία DataFrame από το dictionary των UUIDs
    mapping_df = pd.DataFrame(list(player_uuid_map.items()), columns=["player_name", "uuid"])

    # Αποθήκευση CSV
    mapping_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    # Debug log για επιβεβαίωση
    print(f"✅ Player UUID mapping saved to: {os.path.abspath(output_path)}")

    # (Προαιρετικά) κάνε flush του filesystem cache αν τρέχει σε Linux
    try:
        os.sync()
    except AttributeError:
        pass

#----------------------------------------------------------------
# 12/11 

def assign_player_uuids(df: pd.DataFrame) -> tuple:
    """
    Assigns a unique UUID to each unique player across all seasons.
    Uses normalized player name as the unique identifier.
    """
    print("\nAssigning UUIDs to Players...")

    unique_players = df['Player Name Norm'].unique()
    print(f"  -> Found {len(unique_players):,} unique players")

    player_uuid_map = {
        player_name: str(uuid_module.uuid4())  # Changed here
        for player_name in unique_players
    }

    df['Player UUID'] = df['Player Name Norm'].map(player_uuid_map)

    print(f"✅ UUIDs assigned to all players")
    print(f"📋 Sample mappings:")
    for i, (player, player_uuid) in enumerate(list(player_uuid_map.items())[:5]):
        print(f"   {player}: {player_uuid}")

    return df, player_uuid_map

def save_player_uuid_mapping(df, player_uuid_map, output_path=None):
    """
    Σώζει το mapping στο root/output δίπλα στο training_data.csv
    με όλες τις στήλες: Player UUID, Player Name, Player Name Norm, Web Name.
    """
    # 1) Αν δεν δόθηκε path, γράφουμε δίπλα στο OUTPUT_FILE
    if output_path is None:
        output_dir = OUTPUT_DIR  # <-- root/output
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "player_uuid_mapping.csv")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 2) Φτιάχνουμε το πλήρες mapping dataframe με τις σωστές στήλες
    mapping_df = df[['Player UUID', 'Player Name', 'Player Name Norm', 'Web Name']].drop_duplicates()
    mapping_df = mapping_df.sort_values('Player Name Norm').reset_index(drop=True)

    # 3) Σώζουμε το αρχείο στο σωστό σημείο
    mapping_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ Player UUID mapping saved correctly to: {os.path.abspath(output_path)}")
    print(f"   Rows: {len(mapping_df):,} | Columns: {list(mapping_df.columns)}")


#---------------------------αλλο cell
# 1) Φτιάξε τα UUIDs ΣΤΟ df_lagged (το τελικό πριν το export)
df_lagged, player_uuid_map = assign_player_uuids(df_lagged)

# 2) Σώσε το mapping ΔΙΠΛΑ στο training_data.csv (root/output)
mapping_path = os.path.join(OUTPUT_DIR, "player_uuid_mapping.csv")
save_player_uuid_mapping(df_lagged, player_uuid_map, output_path=mapping_path)


#--------------------------αλλο cell 
# === VERIFY THAT PLAYER_UUID_MAPPING SAVED CORRECTLY ===
import pandas as pd, os

p = os.path.join("output", "player_uuid_mapping.csv")
print("✅ Saved mapping verified at:", os.path.abspath(p))

# Προεπισκόπηση των πρώτων γραμμών για έλεγχο
mapping_preview = pd.read_csv(p)
display(mapping_preview.head(10))
print(f"Total rows: {len(mapping_preview):,}")
print(f"Columns: {list(mapping_preview.columns)}")


#--------------------------αλλο cell
check_path = os.path.join(os.path.dirname(OUTPUT_FILE), "player_uuid_mapping.csv")
print("\n🔍 Does mapping file exist?", os.path.exists(check_path))
if os.path.exists(check_path):
    print("📏 File size:", os.path.getsize(check_path), "bytes")
    