import pandas as pd
import numpy as np
from pathlib import Path

def load_player_teams():
    """Load player-to-team mapping from players_raw.csv"""
    print("\n📂 Loading player team assignments...")
    
    players_file = Path("data/2018-19/players_raw.csv")
    if not players_file.exists():
        # Try alternative names
        for alt_name in ['player_idlist.csv', 'players.csv']:
            alt_file = Path(f"data/2018-19/{alt_name}")
            if alt_file.exists():
                players_file = alt_file
                break
    
    if not players_file.exists():
        print(f"❌ Could not find player data file in data/2018-19/")
        return None
    
    print(f"✅ Found: {players_file}")
    players = pd.read_csv(players_file)
    
    print(f"📋 Columns in players file: {list(players.columns)[:10]}...")
    
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
    print(f"   Sample: {dict(list(player_team_map.items())[:3])}")
    
    return player_team_map


def load_teams_mapping():
    """Load team ID to team name mapping"""
    print("\n📂 Loading team name mappings...")
    
    master_teams_file = Path("data/master_team_list.csv")
    if not master_teams_file.exists():
        print(f"❌ Master team list not found")
        return None
    
    team_map = pd.read_csv(master_teams_file)
    team_map_2018 = team_map[team_map['season'] == '2018-19']
    
    id_to_name = dict(zip(team_map_2018['team'], team_map_2018['team_name']))
    print(f"✅ Loaded {len(id_to_name)} teams")
    print(f"   Sample: {dict(list(id_to_name.items())[:3])}")
    
    return id_to_name


def fix_2018_team_data(df_2018, player_team_map, id_to_name):
    """Fill team data using player-to-team mapping"""
    print("\n🔄 FILLING TEAM DATA FOR 2018-19")
    print("=" * 70)
    
    # Ensure Code column is numeric
    df_2018['Code'] = pd.to_numeric(df_2018['Code'], errors='coerce').astype('Int64')
    
    # Load gameweek data to get opponent_team and was_home
    print("\n📂 Loading gameweek data for opponent info...")
    gw_path = Path("data/2018-19/gws")
    if not gw_path.exists():
        gw_path = Path("data/2018-19")
    
    all_gw_data = []
    for gw_file in sorted(gw_path.glob("gw*.csv")):
        gw_num = int(gw_file.stem.replace('gw', ''))
        df_gw = pd.read_csv(gw_file)
        df_gw['Gameweek'] = gw_num
        all_gw_data.append(df_gw)
    
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
    
    # Fill Player Team ID from player_team_map
    print("\n🔄 Filling Player Team ID...")
    df_2018['Player Team ID'] = df_2018['Code'].map(player_team_map)
    filled_team_id = df_2018['Player Team ID'].notna().sum()
    print(f"   ✓ Filled: {filled_team_id} / {len(df_2018)} ({filled_team_id/len(df_2018)*100:.1f}%)")
    
    # Fill Player Team Name
    print("🔄 Filling Player Team Name...")
    df_2018['Player Team Name'] = df_2018['Player Team ID'].map(id_to_name)
    filled_team_name = df_2018['Player Team Name'].notna().sum()
    print(f"   ✓ Filled: {filled_team_name} / {len(df_2018)} ({filled_team_name/len(df_2018)*100:.1f}%)")
    
    # Fill Opponent ID
    print("🔄 Filling Opponent ID...")
    df_2018['Opponent ID'] = df_2018.apply(
        lambda row: opponent_lookup.get((row['Code'], row['Gameweek'])),
        axis=1
    )
    filled_opp_id = df_2018['Opponent ID'].notna().sum()
    print(f"   ✓ Filled: {filled_opp_id} / {len(df_2018)} ({filled_opp_id/len(df_2018)*100:.1f}%)")
    
    # Fill Opponent Name
    print("🔄 Filling Opponent Name...")
    df_2018['Opponent ID'] = pd.to_numeric(df_2018['Opponent ID'], errors='coerce').astype('Int64')
    df_2018['Opponent Name'] = df_2018['Opponent ID'].map(id_to_name)
    filled_opp_name = df_2018['Opponent Name'].notna().sum()
    print(f"   ✓ Filled: {filled_opp_name} / {len(df_2018)} ({filled_opp_name/len(df_2018)*100:.1f}%)")
    
    print("\n✅ Team data filling complete!")
    print(f"\n📊 Sample rows:")
    sample_cols = ['Player Name', 'Player Team Name', 'Player Team ID', 'Opponent Name', 'Opponent ID', 'Gameweek']
    print(df_2018[sample_cols].head(5).to_string(index=False))
    
    return df_2018


def fill_opponent_difficulty(df_2018):
    """Fill opponent difficulty using fixtures.csv"""
    print("\n🎯 FILLING OPPONENT DIFFICULTY")
    print("=" * 70)
    
    fixtures_path = Path("data/2018-19/fixtures.csv")
    if not fixtures_path.exists():
        print(f"❌ Fixtures file not found: {fixtures_path}")
        return df_2018
    
    fixtures = pd.read_csv(fixtures_path)
    print(f"📊 Loaded {len(fixtures)} fixtures")
    
    # Prepare fixtures
    if 'event' in fixtures.columns:
        fixtures['Gameweek'] = fixtures['event']
    
    fixtures['team_h'] = pd.to_numeric(fixtures['team_h'], errors='coerce').astype('Int64')
    fixtures['team_a'] = pd.to_numeric(fixtures['team_a'], errors='coerce').astype('Int64')
    fixtures['Gameweek'] = pd.to_numeric(fixtures['Gameweek'], errors='coerce').astype('Int64')
    
    # Ensure df columns are correct type
    df_2018['Player Team ID'] = pd.to_numeric(df_2018['Player Team ID'], errors='coerce').astype('Int64')
    df_2018['Opponent ID'] = pd.to_numeric(df_2018['Opponent ID'], errors='coerce').astype('Int64')
    df_2018['Gameweek'] = pd.to_numeric(df_2018['Gameweek'], errors='coerce').astype('Int64')
    
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
    df_2018['Opponent Difficulty'] = df_2018.apply(get_difficulty, axis=1)
    
    filled = df_2018['Opponent Difficulty'].notna().sum()
    print(f"✅ Filled: {filled} / {len(df_2018)} ({filled/len(df_2018)*100:.1f}%)")
    
    if filled > 0:
        print(f"\n📋 Sample filled rows:")
        sample = df_2018[df_2018['Opponent Difficulty'].notna()][
            ['Player Name', 'Player Team Name', 'Opponent Name', 'Is Home', 'Gameweek', 'Opponent Difficulty']
        ].head(5)
        print(sample.to_string(index=False))
    
    return df_2018


if __name__ == "__main__":
    print("=" * 70)
    print("FIX 2018-19 SEASON DATA")
    print("=" * 70)
    
    # Load mappings
    player_team_map = load_player_teams()
    if player_team_map is None:
        print("\n❌ Cannot proceed without player team assignments")
        exit(1)
    
    id_to_name = load_teams_mapping()
    if id_to_name is None:
        print("\n❌ Cannot proceed without team name mappings")
        exit(1)
    
    # Load training data
    input_csv = Path("output/training_data.csv")
    print(f"\n📥 Loading {input_csv} ...")
    df = pd.read_csv(input_csv)
    
    # Filter 2018-19
    mask_2018 = df['season'] == '2018-19'
    df_2018 = df[mask_2018].copy()
    print(f"🔎 Found {len(df_2018)} rows for 2018-19")
    
    # Fix team data
    df_2018_fixed = fix_2018_team_data(df_2018, player_team_map, id_to_name)
    
    # Fill opponent difficulty
    df_2018_fixed = fill_opponent_difficulty(df_2018_fixed)
    
    # Update main dataframe
    print("\n💾 Updating main dataframe...")
    for col in ['Player Team Name', 'Player Team ID', 'Opponent Name', 'Opponent ID', 'Opponent Difficulty']:
        if col in df_2018_fixed.columns:
            df.loc[mask_2018, col] = df_2018_fixed[col].values
    
    # Save
    df.to_csv(input_csv, index=False, encoding='utf-8-sig')
    print(f"✅ Saved to {input_csv}")
    
    # Final stats
    print(f"\n" + "=" * 70)
    print(f"📊 FINAL STATS FOR 2018-19:")
    print("=" * 70)
    for col in ['Player Team Name', 'Player Team ID', 'Opponent Name', 'Opponent ID', 'Opponent Difficulty']:
        count = df[mask_2018][col].notna().sum()
        total = len(df[mask_2018])
        pct = count/total*100 if total > 0 else 0
        print(f"   {col:25s}: {count:5d} / {total} ({pct:5.1f}%)")
    
    print("\n🎉 DONE!")