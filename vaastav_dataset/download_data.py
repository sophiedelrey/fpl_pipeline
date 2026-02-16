import os
import requests
from pathlib import Path

# Configuration
BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
SEASONS = ["2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
DATA_DIR = "data"

def download_file(url, save_path):
    """
    Download a file from URL and save it to the specified path.
    Returns True if successful, False otherwise.
    """
    if os.path.exists(save_path):
        print("—")  # Already exists
        return True 

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(response.content)
            print("✓")
            return True
        else:
            print(f"✗ (HTTP {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ (Error: {str(e)[:50]})")
        return False

def download_gameweek_data(season, start_gw=1, end_gw=38):
    """
    Download gwX.csv files for each gameweek.
    Handles both old structure (files in root) and new structure (files in gws/).
    """
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    failed = 0
    
    print(f"\n Downloading Gameweek data for {season}...")
    
    # Determine structure: older seasons (2016-2019) use root folder, newer use gws/
    season_year = int(season.split("-")[0])
    use_gws_folder = season_year >= 2020
    
    for gw in range(start_gw, end_gw + 1):
        filename = f"gw{gw}.csv"
        
        # Try new structure first (gws/), then fall back to old structure
        if use_gws_folder:
            url = f"{BASE_URL}/{season}/gws/{filename}"
            save_to = season_path / "gws" / filename
            (season_path / "gws").mkdir(exist_ok=True)
        else:
            # For older seasons, try both locations
            url = f"{BASE_URL}/{season}/gws/{filename}"
            save_to = season_path / filename
        
        print(f"  • {filename:12} ", end="", flush=True)
        
        success = download_file(url, save_to)
        
        # If failed and it's an older season, try the root folder
        if not success and not use_gws_folder:
            url_alt = f"{BASE_URL}/{season}/{filename}"
            print(f"  • {filename:12} (retry) ", end="", flush=True)
            success = download_file(url_alt, save_to)
        
        if success:
            successful += 1
        else:
            failed += 1
    
    print(f"  → {successful} files processed, {failed} failed")
    return successful, failed

def download_fixtures(season):
    """Download fixtures.csv for the season."""
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    filename = "fixtures.csv"
    url = f"{BASE_URL}/{season}/{filename}"
    save_to = season_path / filename
    
    print(f"\n Downloading fixtures for {season}...")
    print(f"  • {filename:12} ", end="", flush=True)
    
    return download_file(url, save_to)

def download_teams(season):
    """Download teams.csv for the season."""
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    filename = "teams.csv"
    url = f"{BASE_URL}/{season}/{filename}"
    save_to = season_path / filename
    
    print(f"\n Downloading teams for {season}...")
    print(f"  • {filename:12} ", end="", flush=True)
    
    return download_file(url, save_to)

def download_players_raw(season):
    """Download players_raw.csv for the season."""
    season_path = Path(DATA_DIR) / season
    season_path.mkdir(parents=True, exist_ok=True)
    
    filename = "players_raw.csv"
    url = f"{BASE_URL}/{season}/{filename}"
    save_to = season_path / filename
    
    print(f"\n Downloading player data for {season}...")
    print(f"  • {filename:12} ", end="", flush=True)
    
    return download_file(url, save_to)

def download_season_data(season):
    """Download all data for a specific season."""
    print(f"\n{'='*50}")
    print(f"Season: {season}")
    print(f"{'='*50}")
    
    download_teams(season)
    download_fixtures(season)
    download_players_raw(season)
    
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