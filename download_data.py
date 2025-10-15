import os
import requests
from pathlib import Path

# Configuration
BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
# Add new seasons here, e.g., ["2022-23", "2023-24", "2024-25"]
SEASONS = ["2016-17","2017-18","2018-19","2019-20","2020-21","2021-22","2022-23", "2023-24", "2024-25"]
DATA_DIR = "data"

def download_file(url, save_path):
    """
    Download a file from URL and save it to the specified path.
    Returns True if successful, False otherwise.
    Prints status (✓, —, or ✗) to the console.
    """
    # 1. Check if the file already exists
    if os.path.exists(save_path):
        print("—")  # Exists/Skipped
        return True 

    # 2. Download the file
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            print("✓") # Success
            return True
        else:
            print(f"✗ (HTTP {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ (Error: {e})")
        return False

def download_gameweek_data(season, start_gw=1, end_gw=38):
    """
    Download gwX.csv files for each gameweek.
    """
    # Use 'gws' subdirectory structure as per the FPL data repository
    season_path = Path(DATA_DIR) / season / "gws"
    season_path.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    failed = 0
    
    print(f"\n Downloading Gameweek data for {season}...")
    
    for gw in range(start_gw, end_gw + 1):
        filename = f"gw{gw}.csv"
        url = f"{BASE_URL}/{season}/gws/{filename}"
        save_to = season_path / filename
        
        # Print filename first, then status on the same line
        print(f"  • {filename:12} ", end="", flush=True)
        
        if download_file(url, save_to):
            successful += 1
        else:
            failed += 1
    
    print(f"  → {successful} files processed (existing or downloaded), {failed} failed")
    return successful, failed

def download_fixtures(season):
    """
    Download fixtures.csv for the season.
    """
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    filename = "fixtures.csv"
    url = f"{BASE_URL}/{season}/{filename}"
    save_to = season_path / filename
    
    print(f"\n Downloading fixtures for {season}...")
    print(f"  • {filename:12} ", end="", flush=True)
    
    return download_file(url, save_to)

def download_teams(season):
    """
    Download teams.csv for the season.
    """
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    filename = "teams.csv"
    url = f"{BASE_URL}/{season}/{filename}"
    save_to = season_path / filename
    
    print(f"\n Downloading teams for {season}...")
    print(f"  • {filename:12} ", end="", flush=True)
    
    return download_file(url, save_to)

def download_players_raw(season):
    """
    Download players_raw.csv for the season (contains all player data).
    """
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    filename = "players_raw.csv"
    url = f"{BASE_URL}/{season}/{filename}"
    save_to = season_path / filename
    
    print(f"\n Downloading player data for {season}...")
    print(f"  • {filename:12} ", end="", flush=True)
    
    return download_file(url, save_to)

def download_season_data(season):
    """
    Download all data for a specific season.
    """
    print(f"\n{'='*50}")
    print(f"Season: {season}")
    print(f"{'='*50}")
    
    # Download main files
    download_teams(season)
    download_fixtures(season)
    download_players_raw(season)
    
    # Download gameweek data
    gw_success, gw_failed = download_gameweek_data(season)
    
    return gw_success, gw_failed

if __name__ == "__main__":
    print("Fantasy Premier League Data Downloader")
    print(f"Data will be saved to: {Path(DATA_DIR).absolute()}")
    
    total_success = 0
    total_failed = 0
    
    for season in SEASONS:
        success, failed = download_season_data(season)
        total_success += success
        total_failed += failed
    
    print(f"\n{'='*50}")
    print(f"Download Complete!")
    print(f"   Total files processed: {total_success}")
    print(f"   Total failures: {total_failed}")
    print(f"{'='*50}\n")
