import pandas as pd
import numpy as np
from pathlib import Path

def load_player_teams_2024_25():
    """Load player-to-team mapping from players_raw.csv for 2024-25"""
    print("\n📂 Loading player team assignments for 2024-25...")
    
    players_file = Path("data/2024-25/players_raw.csv")
    if not players_file.exists():
        print(f"❌ Could not find player data file: {players_file}")
        return None
    
    print(f"✅ Found: {players_file}")
    players = pd.read_csv(players_file)
    
    print(f"📋 Columns in players file: {list(players.columns)[:20]}...")
    
    # Identify the ID column (could be 'id', 'element', or 'code')
    id_col = None
    for possible_id in ['id', 'element', 'code']:
        if possible_id in players.columns:
            id_col = possible_id
            break
    
    # Identify the team column
    team_col = None
    for possible_team in ['team', 'team_id', 'team_code']:
        if possible_team in players.columns:
            team_col = possible_team
            break
    
    if not id_col or not team_col:
        print(f"❌ Could not find ID or team columns")
        print(f"   Available columns: {list(players.columns)}")
        return None
    
    print(f"✓ Using ID column: {id_col}")
    print(f"✓ Using team column: {team_col}")
    
    # Create mapping
    players[id_col] = pd.to_numeric(players[id_col], errors='coerce').astype('Int64')
    players[team_col] = pd.to_numeric(players[team_col], errors='coerce').astype('Int64')
    
    player_team_map = dict(zip(players[id_col], players[team_col]))
    player_team_map = {k: v for k, v in player_team_map.items() if pd.notna(k) and pd.notna(v)}
    
    print(f"✅ Created mapping for {len(player_team_map)} players")
    print(f"   Sample mappings: {dict(list(player_team_map.items())[:5])}")
    
    return player_team_map


def load_teams_mapping_2024_25():
    """Load team ID to team name mapping from teams.csv"""
    print("\n📂 Loading team name mappings for 2024-25...")
    
    teams_file = Path("data/2024-25/teams.csv")
    if not teams_file.exists():
        print(f"❌ Teams file not found: {teams_file}")
        return None
    
    teams = pd.read_csv(teams_file)
    print(f"📋 Teams file columns: {list(teams.columns)}")
    
    # Find ID and name columns
    id_col = 'id' if 'id' in teams.columns else 'code'
    name_col = 'name' if 'name' in teams.columns else 'team_name'
    
    teams[id_col] = pd.to_numeric(teams[id_col], errors='coerce').astype('Int64')
    
    id_to_name = dict(zip(teams[id_col], teams[name_col]))
    id_to_name = {k: v for k, v in id_to_name.items() if pd.notna(k)}
    
    print(f"✅ Loaded {len(id_to_name)} teams")
    print(f"   Teams: {list(id_to_name.values())}")
    
    return id_to_name


def load_opponent_data_2024_25():
    """Load opponent team data from gameweek files"""
    print("\n📂 Loading gameweek data for opponent info...")
    
    gw_path = Path("data/2024-25/gws")
    if not gw_path.exists():
        gw_path = Path("data/2024-25")
    
    all_gw_data = []
    for gw_file in sorted(gw_path.glob("gw*.csv")):
        try:
            gw_num = int(gw_file.stem.replace('gw', ''))
            df_gw = pd.read_csv(gw_file)
            df_gw['Gameweek'] = gw_num
            all_gw_data.append(df_gw)
        except Exception as e:
            print(f"  ⚠️  Error reading {gw_file.name}: {e}")
            continue
    
    if not all_gw_data:
        print(f"❌ No gameweek files found in {gw_path}")
        return None
    
    df_raw = pd.concat(all_gw_data, ignore_index=True)
    df_raw['element'] = pd.to_numeric(df_raw['element'], errors='coerce').astype('Int64')
    df_raw['opponent_team'] = pd.to_numeric(df_raw['opponent_team'], errors='coerce').astype('Int64')
    
    print(f"✅ Loaded {len(df_raw)} gameweek records")
    
    # Create lookup: (element, gameweek) -> opponent_team
    opponent_lookup = {}
    for _, row in df_raw.iterrows():
        key = (row['element'], row['Gameweek'])
        opponent_lookup[key] = row['opponent_team']
    
    print(f"✅ Created opponent lookup with {len(opponent_lookup)} entries")
    
    return opponent_lookup


def fix_2024_25_data(df_2024, player_team_map, id_to_name, opponent_lookup):
    """Fill team data for 2024-25 season"""
    print("\n🔄 FILLING TEAM DATA FOR 2024-25")
    print("=" * 70)
    
    # Ensure Code column is numeric
    df_2024['Code'] = pd.to_numeric(df_2024['Code'], errors='coerce').astype('Int64')
    df_2024['Gameweek'] = pd.to_numeric(df_2024['Gameweek'], errors='coerce').astype('Int64')
    
    # Fill Player Team ID from player_team_map
    print("\n🔄 Filling Player Team ID...")
    df_2024['Player Team ID'] = df_2024['Code'].map(player_team_map)
    filled_team_id = df_2024['Player Team ID'].notna().sum()
    print(f"   ✓ Filled: {filled_team_id} / {len(df_2024)} ({filled_team_id/len(df_2024)*100:.1f}%)")
    
    # Fill Player Team Name
    print("🔄 Filling Player Team Name...")
    df_2024['Player Team ID'] = pd.to_numeric(df_2024['Player Team ID'], errors='coerce').astype('Int64')
    df_2024['Player Team Name'] = df_2024['Player Team ID'].map(id_to_name)
    filled_team_name = df_2024['Player Team Name'].notna().sum()
    print(f"   ✓ Filled: {filled_team_name} / {len(df_2024)} ({filled_team_name/len(df_2024)*100:.1f}%)")
    
    # Fill Opponent ID
    print("🔄 Filling Opponent ID...")
    df_2024['Opponent ID'] = df_2024.apply(
        lambda row: opponent_lookup.get((row['Code'], row['Gameweek'])),
        axis=1
    )
    filled_opp_id = df_2024['Opponent ID'].notna().sum()
    print(f"   ✓ Filled: {filled_opp_id} / {len(df_2024)} ({filled_opp_id/len(df_2024)*100:.1f}%)")
    
    # Fill Opponent Name
    print("🔄 Filling Opponent Name...")
    df_2024['Opponent ID'] = pd.to_numeric(df_2024['Opponent ID'], errors='coerce').astype('Int64')
    df_2024['Opponent Name'] = df_2024['Opponent ID'].map(id_to_name)
    filled_opp_name = df_2024['Opponent Name'].notna().sum()
    print(f"   ✓ Filled: {filled_opp_name} / {len(df_2024)} ({filled_opp_name/len(df_2024)*100:.1f}%)")
    
    print("\n✅ Team data filling complete!")
    print(f"\n📊 Sample rows:")
    sample_cols = ['Player Name', 'Player Team Name', 'Player Team ID', 'Opponent Name', 'Opponent ID', 'Gameweek']
    available_cols = [c for c in sample_cols if c in df_2024.columns]
    print(df_2024[available_cols].head(5).to_string(index=False))
    
    return df_2024


def fill_opponent_difficulty_2024_25(df_2024):
    """Fill opponent difficulty using fixtures.csv"""
    print("\n🎯 FILLING OPPONENT DIFFICULTY")
    print("=" * 70)
    
    fixtures_path = Path("data/2024-25/fixtures.csv")
    if not fixtures_path.exists():
        print(f"❌ Fixtures file not found: {fixtures_path}")
        return df_2024
    
    fixtures = pd.read_csv(fixtures_path)
    print(f"📊 Loaded {len(fixtures)} fixtures")
    
    # Prepare fixtures
    if 'event' in fixtures.columns:
        fixtures['Gameweek'] = fixtures['event']
    
    fixtures['team_h'] = pd.to_numeric(fixtures['team_h'], errors='coerce').astype('Int64')
    fixtures['team_a'] = pd.to_numeric(fixtures['team_a'], errors='coerce').astype('Int64')
    fixtures['Gameweek'] = pd.to_numeric(fixtures['Gameweek'], errors='coerce').astype('Int64')
    
    # Ensure df columns are correct type
    df_2024['Player Team ID'] = pd.to_numeric(df_2024['Player Team ID'], errors='coerce').astype('Int64')
    df_2024['Opponent ID'] = pd.to_numeric(df_2024['Opponent ID'], errors='coerce').astype('Int64')
    df_2024['Gameweek'] = pd.to_numeric(df_2024['Gameweek'], errors='coerce').astype('Int64')
    
    # Check if difficulty columns exist
    if 'team_h_difficulty' not in fixtures.columns or 'team_a_difficulty' not in fixtures.columns:
        print(f"⚠️  Warning: Difficulty columns not found in fixtures")
        return df_2024
    
    def get_difficulty(row):
        if pd.isna(row['Player Team ID']) or pd.isna(row['Opponent ID']) or pd.isna(row['Gameweek']):
            return None
        
        if row['Is Home']:
            # Player's team is home, opponent is away
            match = fixtures[
                (fixtures['team_h'] == row['Player Team ID']) &
                (fixtures['team_a'] == row['Opponent ID']) &
                (fixtures['Gameweek'] == row['Gameweek'])
            ]
            if len(match) > 0:
                return match['team_a_difficulty'].values[0]
        else:
            # Player's team is away, opponent is home
            match = fixtures[
                (fixtures['team_a'] == row['Player Team ID']) &
                (fixtures['team_h'] == row['Opponent ID']) &
                (fixtures['Gameweek'] == row['Gameweek'])
            ]
            if len(match) > 0:
                return match['team_h_difficulty'].values[0]
        
        return None
    
    print("🔄 Calculating opponent difficulties...")
    df_2024['Opponent Difficulty'] = df_2024.apply(get_difficulty, axis=1)
    
    filled = df_2024['Opponent Difficulty'].notna().sum()
    print(f"✅ Filled: {filled} / {len(df_2024)} ({filled/len(df_2024)*100:.1f}%)")
    
    if filled > 0:
        print(f"\n📋 Sample filled rows:")
        sample = df_2024[df_2024['Opponent Difficulty'].notna()][
            ['Player Name', 'Player Team Name', 'Opponent Name', 'Is Home', 'Gameweek', 'Opponent Difficulty']
        ].head(5)
        print(sample.to_string(index=False))
    
    return df_2024


if __name__ == "__main__":
    print("=" * 70)
    print("FIX 2024-25 SEASON DATA")
    print("=" * 70)
    
    # Load mappings
    player_team_map = load_player_teams_2024_25()
    if player_team_map is None:
        print("\n❌ Cannot proceed without player team assignments")
        exit(1)
    
    id_to_name = load_teams_mapping_2024_25()
    if id_to_name is None:
        print("\n❌ Cannot proceed without team name mappings")
        exit(1)
    
    opponent_lookup = load_opponent_data_2024_25()
    if opponent_lookup is None:
        print("\n❌ Cannot proceed without opponent data")
        exit(1)
    
    # Load training data
    input_csv = Path("output/training_data.csv")
    if not input_csv.exists():
        print(f"\n❌ Training data not found: {input_csv}")
        exit(1)
    
    print(f"\n📥 Loading {input_csv} ...")
    df = pd.read_csv(input_csv)
    
    # Filter 2024-25
    mask_2024 = df['season'] == '2024-25'
    df_2024 = df[mask_2024].copy()
    print(f"🔎 Found {len(df_2024)} rows for 2024-25")
    
    if len(df_2024) == 0:
        print("\n⚠️  No 2024-25 data found in training_data.csv")
        exit(0)
    
    # Fix team data
    df_2024_fixed = fix_2024_25_data(df_2024, player_team_map, id_to_name, opponent_lookup)
    
    # Fill opponent difficulty
    df_2024_fixed = fill_opponent_difficulty_2024_25(df_2024_fixed)
    
    # Update main dataframe
    print("\n💾 Updating main dataframe...")
    for col in ['Player Team Name', 'Player Team ID', 'Opponent Name', 'Opponent ID', 'Opponent Difficulty']:
        if col in df_2024_fixed.columns:
            df.loc[mask_2024, col] = df_2024_fixed[col].values
    
    # Create backup
    backup_path = Path("output/training_data_backup_before_2024-25_fix.csv")
    print(f"\n💾 Creating backup at {backup_path}...")
    df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    
    # Save updated data
    df.to_csv(input_csv, index=False, encoding='utf-8-sig')
    print(f"✅ Saved updated data to {input_csv}")
    
    # Final stats
    print(f"\n" + "=" * 70)
    print(f"📊 FINAL STATS FOR 2024-25:")
    print("=" * 70)
    for col in ['Player Team Name', 'Player Team ID', 'Opponent Name', 'Opponent ID', 'Opponent Difficulty']:
        if col in df.columns:
            count = df[mask_2024][col].notna().sum()
            total = len(df[mask_2024])
            pct = count/total*100 if total > 0 else 0
            print(f"   {col:25s}: {count:5d} / {total} ({pct:5.1f}%)")
    
    print("\n🎉 DONE!")
    print(f"💡 If something went wrong, restore from: {backup_path}")