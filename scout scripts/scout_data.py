"""
Fantasy Football Scout Web Scraper
Extracts per-gameweek player and team statistics from FFS Members Area
"""

import os
import time
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class FFScraper:
    """Fantasy Football Scout data scraper"""
    
    def __init__(self, season="2024-25", headless=False):
        self.season = season
        self.base_url = "https://members.fantasyfootballscout.co.uk"
        self.data_dir = Path("data/fpl_scout") / season
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 15)
        
        print(f"✓ Chrome driver initialized for season {season}")
    
    def login(self, username=None, password=None):
        """Login to Fantasy Football Scout"""
        username = username or os.getenv("FFS_USERNAME")
        password = password or os.getenv("FFS_PASSWORD")
        
        if not username or not password:
            raise ValueError(
                "Please provide FFS credentials via parameters or .env file "
                "(FFS_USERNAME and FFS_PASSWORD)"
            )
        
        print("\n→ Logging in to Fantasy Football Scout...")
        self.driver.get(f"{self.base_url}/login/")
        
        # Wait for and fill login form
        username_field = self.wait.until(
            EC.presence_of_element_located((By.ID, "user_login"))
        )
        password_field = self.driver.find_element(By.ID, "user_pass")
        
        username_field.send_keys(username)
        password_field.send_keys(password)
        
        # Submit login
        login_button = self.driver.find_element(By.ID, "wp-submit")
        login_button.click()
        
        # Wait for redirect to members area
        time.sleep(3)
        
        if "members-area" in self.driver.current_url or "members" in self.driver.current_url:
            print("✓ Successfully logged in!")
        else:
            raise Exception("Login failed! Check your credentials.")
    
    def extract_table_data(self, gameweek):
        """Extract DataTable data for current gameweek"""
        script = """
        const playerData = $('.dataTable').DataTable().data().toArray();
        const columns = $('.dataTable').DataTable().settings()[0].aoColumns
            .map(col => col.sTitle || col.mData)
            .filter((col, idx) => idx !== 0);
        
        return playerData.map(row => {
            const player = {};
            columns.forEach((col, idx) => {
                const cellIdx = idx + 1;
                if (cellIdx === 1 || cellIdx === 2) {
                    const temp = document.createElement('div');
                    temp.innerHTML = row[cellIdx];
                    player[col] = temp.textContent.trim();
                } else {
                    player[col] = row[cellIdx];
                }
            });
            return player;
        });
        """
        
        data = self.driver.execute_script(script)
        
        # Add gameweek column
        for row in data:
            row['gameweek'] = gameweek
        
        return data
    
    def set_gameweek_filter(self, gameweek_from, gameweek_to=None):
        """Set gameweek filter on stats page"""
        if gameweek_to is None:
            gameweek_to = gameweek_from
        
        # Find and set 'From' dropdown
        from_selects = self.driver.find_elements(By.TAG_NAME, "select")
        from_dropdown = None
        to_dropdown = None
        
        for select in from_selects:
            options = [opt.get_attribute("value") for opt in select.find_elements(By.TAG_NAME, "option")]
            if "1" in options and len(options) > 30:  # Likely the gameweek dropdown
                if from_dropdown is None:
                    from_dropdown = select
                else:
                    to_dropdown = select
                    break
        
        if from_dropdown and to_dropdown:
            Select(from_dropdown).select_by_value(str(gameweek_from))
            Select(to_dropdown).select_by_value(str(gameweek_to))
            
            # Click filter button
            filter_button = self.driver.find_element(
                By.XPATH, "//button[contains(text(), 'FILTER')] | //input[@value='FILTER']"
            )
            filter_button.click()
            
            # Wait for table to reload
            time.sleep(3)
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dataTable")))
            time.sleep(2)  # Extra buffer for DataTables to finish rendering
            
            return True
        
        return False
    
    def scrape_players(self, start_gw=1, end_gw=38):
        """Scrape per-gameweek player data"""
        print(f"\n{'='*60}")
        print(f"Scraping Player Data: Gameweeks {start_gw} to {end_gw}")
        print(f"{'='*60}\n")
        
        # Navigate to All Players page
        self.driver.get(f"{self.base_url}/player-stats/all-players/")
        time.sleep(4)
        
        all_data = []
        
        for gw in range(start_gw, end_gw + 1):
            print(f"[{gw}/{end_gw}] Processing Gameweek {gw}...", end=" ")
            
            try:
                # Set filter to single gameweek
                success = self.set_gameweek_filter(gw, gw)
                
                if not success:
                    print("✗ Failed to set filter")
                    continue
                
                # Extract data
                gw_data = self.extract_table_data(gw)
                
                if gw_data:
                    all_data.extend(gw_data)
                    print(f"✓ Extracted {len(gw_data)} players")
                else:
                    print("⚠ No data found")
                
                # Small delay between requests
                time.sleep(1.5)
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                continue
        
        # Convert to DataFrame and save
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Reorder columns to put gameweek first
            cols = ['gameweek'] + [col for col in df.columns if col != 'gameweek']
            df = df[cols]
            
            # Save to CSV
            output_file = self.data_dir / f"players_gw_{start_gw}_to_{end_gw}.csv"
            df.to_csv(output_file, index=False)
            
            print(f"\n✓ Saved {len(df)} rows to {output_file}")
            print(f"  Players: {df['Name'].nunique() if 'Name' in df.columns else 'N/A'}")
            print(f"  Gameweeks: {df['gameweek'].nunique()}")
            print(f"  Columns: {len(df.columns)}")
            
            return df
        else:
            print("\n✗ No data scraped!")
            return None
    
    def scrape_teams(self, start_gw=1, end_gw=38):
        """Scrape per-gameweek team data"""
        print(f"\n{'='*60}")
        print(f"Scraping Team Data: Gameweeks {start_gw} to {end_gw}")
        print(f"{'='*60}\n")
        
        # Navigate to Team Stats page
        self.driver.get(f"{self.base_url}/team-stats/")
        time.sleep(4)
        
        all_data = []
        
        for gw in range(start_gw, end_gw + 1):
            print(f"[{gw}/{end_gw}] Processing Gameweek {gw}...", end=" ")
            
            try:
                success = self.set_gameweek_filter(gw, gw)
                
                if not success:
                    print("✗ Failed to set filter")
                    continue
                
                gw_data = self.extract_table_data(gw)
                
                if gw_data:
                    all_data.extend(gw_data)
                    print(f"✓ Extracted {len(gw_data)} teams")
                else:
                    print("⚠ No data found")
                
                time.sleep(1.5)
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                continue
        
        if all_data:
            df = pd.DataFrame(all_data)
            cols = ['gameweek'] + [col for col in df.columns if col != 'gameweek']
            df = df[cols]
            
            output_file = self.data_dir / f"teams_gw_{start_gw}_to_{end_gw}.csv"
            df.to_csv(output_file, index=False)
            
            print(f"\n✓ Saved {len(df)} rows to {output_file}")
            print(f"  Teams: {df['Team'].nunique() if 'Team' in df.columns else 20}")
            print(f"  Gameweeks: {df['gameweek'].nunique()}")
            
            return df
        else:
            print("\n✗ No data scraped!")
            return None
    
    def save_metadata(self, players_df=None, teams_df=None):
        """Save scraping metadata"""
        metadata = {
            "season": self.season,
            "scraped_at": datetime.now().isoformat(),
            "players": {
                "rows": len(players_df) if players_df is not None else 0,
                "columns": list(players_df.columns) if players_df is not None else []
            },
            "teams": {
                "rows": len(teams_df) if teams_df is not None else 0,
                "columns": list(teams_df.columns) if teams_df is not None else []
            }
        }
        
        metadata_file = self.data_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✓ Metadata saved to {metadata_file}")
    
    def close(self):
        """Close the browser"""
        self.driver.quit()
        print("\n✓ Browser closed")


def main():
    """Main execution function"""
    
    # Configuration
    SEASON = "2024-25"
    START_GW = 1
    END_GW = 38  # Adjust to current gameweek if season is ongoing
    SCRAPE_PLAYERS = True
    SCRAPE_TEAMS = True
    
    scraper = None
    
    try:
        # Initialize scraper
        scraper = FFScraper(season=SEASON, headless=False)
        
        # Login (credentials from .env file)
        scraper.login()
        
        # Scrape data
        players_df = None
        teams_df = None
        
        if SCRAPE_PLAYERS:
            players_df = scraper.scrape_players(START_GW, END_GW)
        
        if SCRAPE_TEAMS:
            teams_df = scraper.scrape_teams(START_GW, END_GW)
        
        # Save metadata
        scraper.save_metadata(players_df, teams_df)
        
        print("\n" + "="*60)
        print("Scraping Complete!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Scraping interrupted by user")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()