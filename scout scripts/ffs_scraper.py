import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import os
from pathlib import Path
from getpass import getpass

class FFScoutScraper:
    def __init__(self, username, password):
        """
        Initialize the scraper with login credentials.
        
        Args:
            username: Your FFS membership username/email
            password: Your FFS membership password
        """
        self.session = requests.Session()
        self.base_url = "https://members.fantasyfootballscout.co.uk"
        self.main_site = "https://www.fantasyfootballscout.co.uk"
        self.username = username
        self.password = password
        self.logged_in = False
        
        # Set headers to mimic browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def login(self):
        """
        Log in to Fantasy Football Scout members area.
        """
        print("Attempting to log in...")
        
        # Try the main site login first
        login_page_url = f"{self.main_site}/my-account/"
        response = self.session.get(login_page_url)
        
        if response.status_code != 200:
            # Try alternative login URL
            login_page_url = f"{self.main_site}/wp-login.php"
            response = self.session.get(login_page_url)
            
            if response.status_code != 200:
                raise Exception(f"Failed to access login page. Status: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the login form and extract any hidden fields (CSRF tokens, etc.)
        login_data = {
            'log': self.username,
            'pwd': self.password,
            'rememberme': 'forever',
            'wp-submit': 'Log In',
            'redirect_to': self.base_url
        }
        
        # Look for hidden input fields in the form
        form = soup.find('form', {'id': 'loginform'}) or soup.find('form', {'name': 'loginform'})
        if form:
            hidden_inputs = form.find_all('input', {'type': 'hidden'})
            for hidden in hidden_inputs:
                name = hidden.get('name')
                value = hidden.get('value')
                if name and name not in login_data:
                    login_data[name] = value
        
        # Submit login
        login_url = f"{self.main_site}/wp-login.php"
        response = self.session.post(login_url, data=login_data, allow_redirects=True)
        
        # Check if login was successful
        # Try to access the members area
        test_response = self.session.get(self.base_url)
        
        if test_response.status_code == 200:
            # Check if we're actually logged in by looking for logout link or members content
            content = test_response.text.lower()
            if 'logout' in content or 'dashboard' in content or 'member' in content:
                self.logged_in = True
                print("✓ Successfully logged in!")
                return True
        
        print("✗ Login may have failed. Please check credentials.")
        print(f"   Response URL: {test_response.url}")
        print(f"   Status Code: {test_response.status_code}")
        return False
    
    def get_gameweek_data(self, gameweek=None):
        """
        Scrape player stats for a specific gameweek.
        
        Args:
            gameweek: Gameweek number (None for current/all players view)
            
        Returns:
            pandas DataFrame with player statistics
        """
        if not self.logged_in:
            raise Exception("Not logged in. Call login() first.")
        
        # Construct URL based on gameweek
        if gameweek:
            url = f"{self.base_url}/player-stats/all-players/?gw={gameweek}"
            print(f"Fetching data for Gameweek {gameweek}...")
        else:
            url = f"{self.base_url}/player-stats/all-players/"
            print("Fetching overall player data...")
        
        response = self.session.get(url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data. Status: {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the DataTable
        table = soup.find('table', {'class': 'dataTable'})
        
        if not table:
            raise Exception("Could not find player stats table. Page structure may have changed.")
        
        # Extract headers
        headers = []
        thead = table.find('thead')
        if thead:
            header_rows = thead.find_all('tr')
            for row in header_rows:
                ths = row.find_all('th')
                for th in ths:
                    header_text = th.get_text(strip=True)
                    if header_text and header_text not in headers:
                        headers.append(header_text)
        
        # If headers are empty, create default ones
        if not headers:
            headers = ['Select', 'Player', 'Team', 'Pos', 'Price', 'Points', 'Minutes', 'Goals', 'Assists']
        
        # Extract table body data
        players_data = []
        tbody = table.find('tbody')
        
        if tbody:
            rows = tbody.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = []
                
                for idx, cell in enumerate(cells):
                    # Clean HTML and get text
                    cell_text = cell.get_text(strip=True)
                    
                    # For player name and team columns, they might have links
                    if idx in [1, 2]:  # Usually player name and team
                        link = cell.find('a')
                        if link:
                            cell_text = link.get_text(strip=True)
                    
                    row_data.append(cell_text)
                
                if row_data:  # Only add non-empty rows
                    players_data.append(row_data)
        
        # Create DataFrame
        # Skip the first column (checkbox) if present
        if headers and headers[0] in ['Select', '', ' ']:
            headers = headers[1:]
            players_data = [row[1:] for row in players_data]
        
        # Ensure data rows match header length
        max_cols = max(len(headers), max([len(row) for row in players_data]) if players_data else 0)
        
        # Pad headers if needed
        while len(headers) < max_cols:
            headers.append(f'Column_{len(headers)}')
        
        # Pad data rows if needed
        players_data = [row + [''] * (max_cols - len(row)) for row in players_data]
        
        df = pd.DataFrame(players_data, columns=headers[:max_cols])
        
        # Add gameweek column
        df['Gameweek'] = gameweek if gameweek else 'Overall'
        df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"✓ Extracted {len(df)} players")
        return df
    
    def get_multiple_gameweeks(self, start_gw, end_gw, delay=2):
        """
        Scrape data for multiple gameweeks.
        
        Args:
            start_gw: Starting gameweek number
            end_gw: Ending gameweek number (inclusive)
            delay: Seconds to wait between requests (be respectful!)
            
        Returns:
            Combined pandas DataFrame with all gameweeks
        """
        all_data = []
        
        for gw in range(start_gw, end_gw + 1):
            try:
                df = self.get_gameweek_data(gameweek=gw)
                all_data.append(df)
                
                # Be respectful with rate limiting
                if gw < end_gw:
                    print(f"Waiting {delay} seconds before next request...")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"✗ Error fetching GW{gw}: {str(e)}")
                continue
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            print(f"\n✓ Total rows collected: {len(combined_df)}")
            return combined_df
        else:
            raise Exception("No data was collected")
    
    def save_to_csv(self, df, filename=None):
        """
        Save DataFrame to CSV file.
        
        Args:
            df: pandas DataFrame to save
            filename: Output filename (auto-generated if None)
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ffs_player_stats_{timestamp}.csv"
        
        # Create output directory if it doesn't exist
        output_dir = Path("ffs_data")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"✓ Data saved to: {filepath}")
        return filepath


def get_credentials():
    """
    Get credentials from environment variables or prompt user.
    Priority: Environment variables > Interactive input
    """
    username = os.getenv('FFS_USERNAME')
    password = os.getenv('FFS_PASSWORD')
    
    if not username or not password:
        print("\n" + "="*60)
        print("CREDENTIALS SETUP")
        print("="*60)
        print("No credentials found in environment variables.")
        print("Please enter your Fantasy Football Scout credentials:\n")
        
        if not username:
            username = input("Email/Username: ").strip()
        if not password:
            password = getpass("Password (hidden): ")
        
        print("\n💡 TIP: To avoid entering credentials each time, set them as")
        print("   environment variables:")
        print("   Windows: set FFS_USERNAME=your_email@example.com")
        print("            set FFS_PASSWORD=your_password")
        print("   Mac/Linux: export FFS_USERNAME=your_email@example.com")
        print("              export FFS_PASSWORD=your_password")
        print("="*60 + "\n")
    
    return username, password


# Main execution
if __name__ == "__main__":
    try:
        # Get credentials (will prompt if not set in environment)
        username, password = get_credentials()
        
        if not username or not password:
            print("✗ Error: Username and password are required!")
            exit(1)
        
        # Initialize scraper
        scraper = FFScoutScraper(username=username, password=password)
        
        # Log in
        if scraper.login():
            
            # ============================================================
            # CONFIGURE YOUR SCRAPING HERE
            # ============================================================
            
            # Option 1: Get current gameweek data only
            # df = scraper.get_gameweek_data()
            # scraper.save_to_csv(df, "current_gameweek.csv")
            
            # Option 2: Get specific gameweek
            # df = scraper.get_gameweek_data(gameweek=15)
            # scraper.save_to_csv(df, "gameweek_15.csv")
            
            # Option 3: Get multiple gameweeks (MASTER TABLE)
            print("\n" + "="*60)
            print("SCRAPING MULTIPLE GAMEWEEKS")
            print("="*60)
            
            # Change these numbers based on what gameweeks you want
            START_GAMEWEEK = 1
            END_GAMEWEEK = 10  # Adjust to current gameweek
            
            df_all = scraper.get_multiple_gameweeks(
                start_gw=START_GAMEWEEK,
                end_gw=END_GAMEWEEK,
                delay=2  # Wait 2 seconds between requests (be respectful!)
            )
            
            scraper.save_to_csv(df_all, f"ffs_master_table_gw{START_GAMEWEEK}_{END_GAMEWEEK}.csv")
            
            print("\n" + "="*60)
            print("✓ SCRAPING COMPLETE!")
            print("="*60)
            print(f"Total players scraped: {len(df_all)}")
            print(f"Gameweeks: {START_GAMEWEEK} to {END_GAMEWEEK}")
            print("Check the 'ffs_data' folder for your CSV file!")
            
        else:
            print("✗ Failed to log in. Please check your credentials.")
            
    except KeyboardInterrupt:
        print("\n\n✗ Scraping cancelled by user.")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")