import pandas as pd
import numpy as np
from pathlib import Path

def diagnose_missing_data():
    """Diagnose why some rows don't have team IDs filled"""
    print("=" * 70)
    print("DIAGNOSING MISSING TEAM IDs")
    print("=" * 70)
    
    # Load training data
    input_csv = Path("output/training_data.csv")
    if not input_csv.exists():
        print(f"❌ Training data not found: {input_csv}")
        return
    
    df = pd.read_csv(input_csv)
    print(f"\n✅ Loaded {len(df):,} rows")
    
    # Find rows with missing data
    missing_player_team = df['Player Team ID'].isna()
    missing_opponent = df['Opponent ID'].isna()
    
    print(f"\n📊 Missing Data Summary:")
    print(f"  Missing Player Team ID: {missing_player_team.sum():,} rows ({missing_player_team.sum()/len(df)*100:.1f}%)")
    print(f"  Missing Opponent ID:    {missing_opponent.sum():,} rows ({missing_opponent.sum()/len(df)*100:.1f}%)")
    
    # Analyze by season
    print(f"\n📊 Missing Data by Season:")
    print(f"{'Season':<12} {'Total Rows':<12} {'Missing Team ID':<18} {'Missing Opp ID':<18}")
    print("-" * 70)
    
    for season in sorted(df['season'].unique()):
        season_mask = df['season'] == season
        total = season_mask.sum()
        missing_team = (season_mask & missing_player_team).sum()
        missing_opp = (season_mask & missing_opponent).sum()
        
        print(f"{season:<12} {total:<12,} {missing_team:<12,} ({missing_team/total*100:>4.1f}%)  {missing_opp:<12,} ({missing_opp/total*100:>4.1f}%)")
    
    # Show sample of missing data
    print(f"\n🔍 Sample rows with missing Player Team ID:")
    sample_missing = df[missing_player_team][['season', 'Gameweek', 'Code', 'Player Name', 'Player Team Name', 'Player Team ID']].head(10)
    print(sample_missing.to_string(index=False))
    
    # Check if Code values are valid
    print(f"\n🔍 Checking Code values for missing rows:")
    missing_codes = df[missing_player_team]['Code']
    print(f"  Missing rows with Code = NaN: {missing_codes.isna().sum():,}")
    print(f"  Missing rows with Code = 0:   {(missing_codes == 0).sum():,}")
    print(f"  Missing rows with valid Code: {(missing_codes.notna() & (missing_codes != 0)).sum():,}")
    
    # Check specific season files
    print(f"\n🔍 Checking source files availability:")
    for season in sorted(df['season'].unique()):
        season_path = Path(f"data/{season}")
        if not season_path.exists():
            print(f"  ❌ {season}: Folder not found")
            continue
        
        # Check for players file
        players_files = list(season_path.glob("players*.csv")) + list(season_path.glob("player_*.csv"))
        has_players = len(players_files) > 0
        
        # Check for gameweek files
        gws_path = season_path / "gws"
        if gws_path.exists():
            gw_files = list(gws_path.glob("gw*.csv"))
        else:
            gw_files = list(season_path.glob("gw*.csv"))
        has_gws = len(gw_files) > 0
        
        status = "✅" if (has_players and has_gws) else "⚠️"
        print(f"  {status} {season}: Players={has_players}, Gameweeks={has_gws} ({len(gw_files)} files)")
    
    # Deep dive into one problematic season
    print(f"\n🔬 DEEP DIVE: Checking data consistency for worst season")
    print("=" * 70)
    
    # Find season with most missing data
    worst_season = None
    max_missing = 0
    for season in df['season'].unique():
        season_mask = df['season'] == season
        missing_count = (season_mask & missing_player_team).sum()
        if missing_count > max_missing and missing_count > 0:
            max_missing = missing_count
            worst_season = season
    
    if worst_season:
        print(f"\nWorst season: {worst_season} ({max_missing:,} missing)")
        
        season_mask = df['season'] == worst_season
        df_season = df[season_mask]
        
        # Load players_raw for this season
        season_path = Path(f"data/{worst_season}")
        for filename in ['players_raw.csv', 'player_idlist.csv', 'players.csv']:
            players_file = season_path / filename
            if players_file.exists():
                print(f"\n✅ Found: {players_file}")
                players = pd.read_csv(players_file)
                print(f"  Columns: {list(players.columns)[:10]}")
                
                # Find ID column
                id_col = None
                for possible_id in ['id', 'element', 'code']:
                    if possible_id in players.columns:
                        id_col = possible_id
                        break
                
                if id_col:
                    players[id_col] = pd.to_numeric(players[id_col], errors='coerce')
                    player_ids_in_source = set(players[id_col].dropna().astype(int))
                    print(f"  Player IDs in source: {len(player_ids_in_source)}")
                    print(f"  Sample IDs: {sorted(list(player_ids_in_source))[:10]}")
                    
                    # Compare with training data
                    codes_in_training = set(df_season['Code'].dropna().astype(int))
                    print(f"\n  Codes in training data: {len(codes_in_training)}")
                    print(f"  Sample codes: {sorted(list(codes_in_training))[:10]}")
                    
                    # Find mismatches
                    codes_not_in_source = codes_in_training - player_ids_in_source
                    if codes_not_in_source:
                        print(f"\n  ⚠️  {len(codes_not_in_source)} codes in training data NOT found in source!")
                        print(f"  Sample missing codes: {sorted(list(codes_not_in_source))[:20]}")
                        
                        # Show which players have these codes
                        missing_codes_mask = df_season['Code'].isin(codes_not_in_source)
                        print(f"\n  Players affected:")
                        affected = df_season[missing_codes_mask][['Code', 'Player Name', 'season']].drop_duplicates().head(10)
                        print(affected.to_string(index=False))
                    else:
                        print(f"\n  ✅ All codes found in source file!")
                
                break
        else:
            print(f"\n❌ No players file found for {worst_season}")
    
    # Check for Code vs element column mismatch
    print(f"\n🔍 Checking for potential column mapping issues:")
    print("=" * 70)
    
    # Load a sample gameweek file and compare
    for season in sorted(df['season'].unique())[:3]:  # Check first 3 seasons
        gw_path = Path(f"data/{season}/gws")
        if not gw_path.exists():
            gw_path = Path(f"data/{season}")
        
        gw_files = list(gw_path.glob("gw*.csv"))
        if gw_files:
            sample_gw = pd.read_csv(gw_files[0])
            
            # Check what ID columns exist
            id_cols = [col for col in sample_gw.columns if col in ['element', 'id', 'code', 'player_id']]
            print(f"\n  {season} - GW1 ID columns: {id_cols}")
            
            if 'element' in sample_gw.columns:
                print(f"    Sample 'element' values: {sample_gw['element'].head(5).tolist()}")
            
            # Compare with training data Code values
            season_mask = df['season'] == season
            print(f"    Training data 'Code' values: {df[season_mask]['Code'].head(5).tolist()}")


if __name__ == "__main__":
    diagnose_missing_data()