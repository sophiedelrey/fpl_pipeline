import pandas as pd
import numpy as np
from pathlib import Path

def load_master_team_mapping():
    """Load team ID to name mapping from master_team_list.csv"""
    print("\n📂 Loading Master Team List...")
    
    master_file = Path("data/master_team_list.csv")
    if not master_file.exists():
        print(f"❌ Master team list not found: {master_file}")
        return None
    
    teams = pd.read_csv(master_file)
    print(f"✅ Loaded {len(teams)} team-season mappings")
    print(f"📋 Columns: {list(teams.columns)}")
    print(f"📊 Seasons covered: {sorted(teams['season'].unique())}")
    
    # Create dictionary: {season: {team_id: team_name}}
    team_mapping = {}
    for season in teams['season'].unique():
        season_teams = teams[teams['season'] == season]
        # Assuming columns are 'team' (ID) and 'team_name'
        id_col = 'team' if 'team' in teams.columns else 'id'
        name_col = 'team_name' if 'team_name' in teams.columns else 'name'
        
        team_mapping[season] = dict(zip(
            season_teams[id_col].astype('Int64'),
            season_teams[name_col]
        ))
    
    print(f"✅ Created mappings for {len(team_mapping)} seasons")
    
    return team_mapping, teams


def load_player_teams_for_season(season):
    """Load player-to-team mapping for a specific season"""
    season_path = Path(f"data/{season}")
    
    if not season_path.exists():
        print(f"  ⚠️  Season folder not found: {season_path}")
        return None
    
    # Try different player file names
    for filename in ['players_raw.csv', 'player_idlist.csv', 'players.csv']:
        players_file = season_path / filename
        if players_file.exists():
            try:
                players = pd.read_csv(players_file)
                
                # Find ID column
                id_col = None
                for possible_id in ['id', 'element', 'code']:
                    if possible_id in players.columns:
                        id_col = possible_id
                        break
                
                # Find team column
                team_col = None
                for possible_team in ['team', 'team_id', 'team_code']:
                    if possible_team in players.columns:
                        team_col = possible_team
                        break
                
                if id_col and team_col:
                    players[id_col] = pd.to_numeric(players[id_col], errors='coerce').astype('Int64')
                    players[team_col] = pd.to_numeric(players[team_col], errors='coerce').astype('Int64')
                    
                    player_team_map = dict(zip(players[id_col], players[team_col]))
                    player_team_map = {k: v for k, v in player_team_map.items() if pd.notna(k) and pd.notna(v)}
                    
                    return player_team_map
            except Exception as e:
                print(f"  ⚠️  Error reading {filename}: {e}")
                continue
    
    return None


def load_opponent_data_for_season(season):
    """Load opponent team data from gameweek files"""
    gw_path = Path(f"data/{season}/gws")
    if not gw_path.exists():
        gw_path = Path(f"data/{season}")
    
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
        return None
    
    df_raw = pd.concat(all_gw_data, ignore_index=True)
    df_raw['element'] = pd.to_numeric(df_raw['element'], errors='coerce').astype('Int64')
    df_raw['opponent_team'] = pd.to_numeric(df_raw['opponent_team'], errors='coerce').astype('Int64')
    
    # Create lookup: (element, gameweek) -> opponent_team
    opponent_lookup = {}
    for _, row in df_raw.iterrows():
        key = (row['element'], row['Gameweek'])
        opponent_lookup[key] = row['opponent_team']
    
    return opponent_lookup


def fix_season_data(df_season, season, team_id_to_name, player_team_map, opponent_lookup):
    """Fix team IDs and names for a specific season"""
    
    # Ensure Code column is numeric
    df_season['Code'] = pd.to_numeric(df_season['Code'], errors='coerce').astype('Int64')
    df_season['Gameweek'] = pd.to_numeric(df_season['Gameweek'], errors='coerce').astype('Int64')
    
    initial_stats = {
        'Player Team ID': df_season['Player Team ID'].notna().sum(),
        'Player Team Name': df_season['Player Team Name'].notna().sum(),
        'Opponent ID': df_season['Opponent ID'].notna().sum(),
        'Opponent Name': df_season['Opponent Name'].notna().sum()
    }
    
    # Fill Player Team ID
    if player_team_map:
        df_season['Player Team ID'] = df_season['Code'].map(player_team_map)
    
    # Fill Player Team Name
    df_season['Player Team ID'] = pd.to_numeric(df_season['Player Team ID'], errors='coerce').astype('Int64')
    df_season['Player Team Name'] = df_season['Player Team ID'].map(team_id_to_name)
    
    # Fill Opponent ID
    if opponent_lookup:
        df_season['Opponent ID'] = df_season.apply(
            lambda row: opponent_lookup.get((row['Code'], row['Gameweek'])),
            axis=1
        )
    
    # Fill Opponent Name
    df_season['Opponent ID'] = pd.to_numeric(df_season['Opponent ID'], errors='coerce').astype('Int64')
    df_season['Opponent Name'] = df_season['Opponent ID'].map(team_id_to_name)
    
    final_stats = {
        'Player Team ID': df_season['Player Team ID'].notna().sum(),
        'Player Team Name': df_season['Player Team Name'].notna().sum(),
        'Opponent ID': df_season['Opponent ID'].notna().sum(),
        'Opponent Name': df_season['Opponent Name'].notna().sum()
    }
    
    # Print improvements
    print(f"\n  📊 Improvements:")
    for col in initial_stats:
        before = initial_stats[col]
        after = final_stats[col]
        diff = after - before
        if diff > 0:
            print(f"    {col:20s}: +{diff:5d} rows filled")
    
    return df_season


def fill_opponent_difficulty_for_season(df_season, season):
    """Fill opponent difficulty from fixtures.csv"""
    fixtures_path = Path(f"data/{season}/fixtures.csv")
    
    if not fixtures_path.exists():
        return df_season
    
    try:
        fixtures = pd.read_csv(fixtures_path)
        
        if 'event' in fixtures.columns:
            fixtures['Gameweek'] = fixtures['event']
        
        # Check if difficulty columns exist
        if 'team_h_difficulty' not in fixtures.columns or 'team_a_difficulty' not in fixtures.columns:
            return df_season
        
        fixtures['team_h'] = pd.to_numeric(fixtures['team_h'], errors='coerce').astype('Int64')
        fixtures['team_a'] = pd.to_numeric(fixtures['team_a'], errors='coerce').astype('Int64')
        fixtures['Gameweek'] = pd.to_numeric(fixtures['Gameweek'], errors='coerce').astype('Int64')
        
        df_season['Player Team ID'] = pd.to_numeric(df_season['Player Team ID'], errors='coerce').astype('Int64')
        df_season['Opponent ID'] = pd.to_numeric(df_season['Opponent ID'], errors='coerce').astype('Int64')
        df_season['Gameweek'] = pd.to_numeric(df_season['Gameweek'], errors='coerce').astype('Int64')
        
        def get_difficulty(row):
            if pd.isna(row['Player Team ID']) or pd.isna(row['Opponent ID']) or pd.isna(row['Gameweek']):
                return None
            
            if row['Is Home']:
                match = fixtures[
                    (fixtures['team_h'] == row['Player Team ID']) &
                    (fixtures['team_a'] == row['Opponent ID']) &
                    (fixtures['Gameweek'] == row['Gameweek'])
                ]
                if len(match) > 0:
                    return match['team_a_difficulty'].values[0]
            else:
                match = fixtures[
                    (fixtures['team_a'] == row['Player Team ID']) &
                    (fixtures['team_h'] == row['Opponent ID']) &
                    (fixtures['Gameweek'] == row['Gameweek'])
                ]
                if len(match) > 0:
                    return match['team_h_difficulty'].values[0]
            
            return None
        
        before = df_season['Opponent Difficulty'].notna().sum()
        df_season['Opponent Difficulty'] = df_season.apply(get_difficulty, axis=1)
        after = df_season['Opponent Difficulty'].notna().sum()
        
        if after > before:
            print(f"    {'Opponent Difficulty':20s}: +{after - before:5d} rows filled")
        
    except Exception as e:
        print(f"  ⚠️  Error filling opponent difficulty: {str(e)[:100]}")
    
    return df_season


if __name__ == "__main__":
    print("=" * 70)
    print("FIX TEAM IDS AND NAMES FOR ALL SEASONS")
    print("=" * 70)
    
    # Load master team mapping
    result = load_master_team_mapping()
    if result is None:
        print("\n❌ Cannot proceed without master team list")
        exit(1)
    
    team_mapping_by_season, master_teams = result
    
    # Load training data
    input_csv = Path("output/training_data.csv")
    if not input_csv.exists():
        print(f"\n❌ Training data not found: {input_csv}")
        exit(1)
    
    print(f"\n📥 Loading {input_csv} ...")
    df = pd.read_csv(input_csv)
    print(f"✅ Loaded {len(df):,} rows")
    
    # Create backup
    backup_path = Path("output/training_data_backup_before_team_ids_fix.csv")
    print(f"\n💾 Creating backup at {backup_path}...")
    df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"✅ Backup created")
    
    # Get all seasons
    seasons = sorted(df['season'].unique())
    print(f"\n🔄 Processing {len(seasons)} seasons: {seasons}")
    
    # Process each season
    for season in seasons:
        print(f"\n{'='*70}")
        print(f"🔄 SEASON: {season}")
        print(f"{'='*70}")
        
        mask = df['season'] == season
        df_season = df[mask].copy()
        
        print(f"  📊 Rows: {len(df_season):,}")
        
        # Get team ID to name mapping for this season
        team_id_to_name = team_mapping_by_season.get(season, {})
        if not team_id_to_name:
            print(f"  ⚠️  No team mapping found in master_team_list.csv")
            continue
        
        print(f"  ✓ Found {len(team_id_to_name)} teams in mapping")
        
        # Load player-team mapping
        player_team_map = load_player_teams_for_season(season)
        if player_team_map:
            print(f"  ✓ Loaded player-team mapping ({len(player_team_map)} players)")
        else:
            print(f"  ⚠️  No player-team mapping found")
        
        # Load opponent data
        opponent_lookup = load_opponent_data_for_season(season)
        if opponent_lookup:
            print(f"  ✓ Loaded opponent data ({len(opponent_lookup)} player-gameweek pairs)")
        else:
            print(f"  ⚠️  No opponent data found")
        
        # Fix the data
        df_season_fixed = fix_season_data(
            df_season, season, team_id_to_name, 
            player_team_map, opponent_lookup
        )
        
        # Fill opponent difficulty
        df_season_fixed = fill_opponent_difficulty_for_season(df_season_fixed, season)
        
        # Update main dataframe
        for col in ['Player Team Name', 'Player Team ID', 'Opponent Name', 
                    'Opponent ID', 'Opponent Difficulty']:
            if col in df_season_fixed.columns:
                df.loc[mask, col] = df_season_fixed[col].values
    
    # Save updated data
    print(f"\n{'='*70}")
    print("💾 SAVING UPDATED DATA")
    print(f"{'='*70}")
    
    df.to_csv(input_csv, index=False, encoding='utf-8-sig')
    print(f"✅ Saved to {input_csv}")
    
    # Final statistics
    print(f"\n{'='*70}")
    print("📊 FINAL STATISTICS (ALL SEASONS)")
    print(f"{'='*70}")
    
    total_rows = len(df)
    for col in ['Player Team Name', 'Player Team ID', 'Opponent Name', 
                'Opponent ID', 'Opponent Difficulty']:
        if col in df.columns:
            filled = df[col].notna().sum()
            pct = (filled / total_rows * 100) if total_rows > 0 else 0
            print(f"  {col:25s}: {filled:6d} / {total_rows:6d} ({pct:5.1f}%)")
    
    print(f"\n{'='*70}")
    print("📊 BREAKDOWN BY SEASON")
    print(f"{'='*70}")
    
    for season in sorted(df['season'].unique()):
        mask = df['season'] == season
        season_rows = mask.sum()
        print(f"\n  Season: {season} ({season_rows:,} rows)")
        
        for col in ['Player Team Name', 'Opponent Name', 'Opponent Difficulty']:
            if col in df.columns:
                filled = df.loc[mask, col].notna().sum()
                pct = (filled / season_rows * 100) if season_rows > 0 else 0
                print(f"    {col:25s}: {filled:5d} ({pct:5.1f}%)")
    
    print("\n🎉 DONE!")
    print(f"💡 If something went wrong, restore from: {backup_path}")