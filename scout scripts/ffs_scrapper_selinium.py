"""
Fantasy Football Scout Scraper - Selenium Version
Handles JavaScript-rendered tables and custom My Stats Tables
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from datetime import datetime
import time
import os
from pathlib import Path
from getpass import getpass


class FFScoutSeleniumScraper:
    def __init__(self, username, password, headless=True):
        """
        Initialize the scraper with Selenium WebDriver.
        
        Args:
            username: Your FFS membership username/email
            password: Your FFS membership password
            headless: Run browser in headless mode (no GUI)
        """
        self.username = username
        self.password = password
        self.driver = None
        self.logged_in = False
        self.headless = headless
        
        # URLs
        self.base_url = "https://members.fantasyfootballscout.co.uk"
        self.main_site = "https://www.fantasyfootballscout.co.uk"
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with appropriate options."""
        print("Setting up browser...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # User agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            # Try webdriver-manager first (automatic ChromeDriver management)
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print("✓ Browser ready (using webdriver-manager)")
            except ImportError:
                # Fallback to manual ChromeDriver
                self.driver = webdriver.Chrome(options=chrome_options)
                print("✓ Browser ready (using system ChromeDriver)")
                
        except Exception as e:
            print(f"✗ Error setting up Chrome driver: {str(e)}")
            print("\n💡 Quick fix: Install webdriver-manager")
            print("   pip install webdriver-manager")
            print("\nThis will automatically download and manage ChromeDriver!")
            raise
    
    def login(self):
        """Log in to Fantasy Football Scout."""
        if not self.driver:
            self.setup_driver()
        
        print("Logging in to Fantasy Football Scout...")
        
        try:
            # Navigate to login page
            self.driver.get(f"{self.main_site}/my-account/")
            time.sleep(3)
            
            # Try to close any cookie banners or popups
            try:
                cookie_buttons = [
                    (By.CSS_SELECTOR, "button.cookie-accept"),
                    (By.CSS_SELECTOR, "button[id*='cookie']"),
                    (By.CSS_SELECTOR, "a.cookie-accept"),
                    (By.XPATH, "//button[contains(text(), 'Accept')]"),
                    (By.XPATH, "//button[contains(text(), 'OK')]"),
                ]
                for selector_type, selector_value in cookie_buttons:
                    try:
                        cookie_btn = self.driver.find_element(selector_type, selector_value)
                        cookie_btn.click()
                        print("✓ Closed cookie banner")
                        time.sleep(1)
                        break
                    except:
                        continue
            except:
                pass
            
            # Scroll to login form
            self.driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)
            
            # Try multiple possible selectors for username field
            wait = WebDriverWait(self.driver, 10)
            username_field = None
            
            selectors = [
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.ID, "log"),
                (By.NAME, "log"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.CSS_SELECTOR, "input[type='email']")
            ]
            
            for selector_type, selector_value in selectors:
                try:
                    username_field = wait.until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✓ Found username field using: {selector_value}")
                    break
                except:
                    continue
            
            if not username_field:
                # Save screenshot for debugging
                self.driver.save_screenshot("login_page_debug.png")
                print("✗ Could not find username field. Screenshot saved to login_page_debug.png")
                print(f"Current URL: {self.driver.current_url}")
                return False
            
            # Scroll element into view and wait
            self.driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
            time.sleep(0.5)
            
            # Enter username using JavaScript if needed
            try:
                username_field.clear()
                username_field.send_keys(self.username)
            except:
                print("⚠ Using JavaScript to enter username")
                self.driver.execute_script(f"arguments[0].value = '{self.username}';", username_field)
            
            # Try multiple possible selectors for password field
            password_field = None
            password_selectors = [
                (By.ID, "password"),
                (By.NAME, "password"),
                (By.ID, "pwd"),
                (By.NAME, "pwd"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            for selector_type, selector_value in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✓ Found password field using: {selector_value}")
                    break
                except:
                    continue
            
            if not password_field:
                print("✗ Could not find password field")
                self.driver.save_screenshot("no_password_field_debug.png")
                return False
            
            # Scroll to password field
            self.driver.execute_script("arguments[0].scrollIntoView(true);", password_field)
            time.sleep(0.5)
            
            # Enter password using JavaScript if needed
            try:
                password_field.clear()
                password_field.send_keys(self.password)
            except:
                print("⚠ Using JavaScript to enter password")
                self.driver.execute_script(f"arguments[0].value = '{self.password}';", password_field)
            
            print("✓ Credentials entered")
            time.sleep(1)
            
            # Try to find and click login button
            login_button = None
            button_selectors = [
                (By.NAME, "login"),
                (By.NAME, "wp-submit"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Log')]"),
                (By.XPATH, "//input[@value='Log In']"),
                (By.CSS_SELECTOR, "button.woocommerce-button"),
            ]
            
            for selector_type, selector_value in button_selectors:
                try:
                    login_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((selector_type, selector_value))
                    )
                    print(f"✓ Found login button using: {selector_value}")
                    break
                except:
                    continue
            
            if login_button:
                try:
                    # Scroll to button
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
                    time.sleep(0.5)
                    # Click using JavaScript to avoid interception
                    self.driver.execute_script("arguments[0].click();", login_button)
                    print("✓ Login button clicked")
                except:
                    print("⚠ Standard click failed, trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", login_button)
            else:
                # Try submitting the form directly
                print("⚠ Login button not found, trying form submit...")
                try:
                    password_field.submit()
                except:
                    self.driver.execute_script("document.querySelector('form').submit();")
            
            # Wait for redirect/login to complete
            print("Waiting for login to complete...")
            time.sleep(5)
            
            # Check if logged in
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            
            print(f"Current URL after login: {current_url}")
            
            # Multiple checks for successful login
            success_indicators = [
                "logout" in page_source,
                "sign out" in page_source,
                "dashboard" in page_source,
                "members.fantasyfootballscout" in current_url,
                "my-account" in current_url and "login" not in page_source
            ]
            
            if any(success_indicators):
                self.logged_in = True
                print("✓ Successfully logged in!")
                return True
            else:
                # Save debug info
                self.driver.save_screenshot("login_failed_debug.png")
                print("✗ Login may have failed. Check credentials.")
                print("   Screenshot saved to login_failed_debug.png")
                
                # Check for error messages
                try:
                    error_msg = self.driver.find_element(By.CSS_SELECTOR, ".woocommerce-error, .error, .login-error")
                    print(f"   Error message: {error_msg.text}")
                except:
                    pass
                
                return False
                
        except TimeoutException:
            print("✗ Timeout waiting for login page elements")
            self.driver.save_screenshot("login_timeout_debug.png")
            print("   Screenshot saved to login_timeout_debug.png")
            return False
        except Exception as e:
            print(f"✗ Login error: {str(e)}")
            self.driver.save_screenshot("login_error_debug.png")
            import traceback
            traceback.print_exc()
            return False
    
    def wait_for_table_load(self, timeout=20):
        """Wait for DataTable to fully load."""
        try:
            wait = WebDriverWait(self.driver, timeout)
            
            # Wait for table to be present
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable")))
            
            # Wait for loading indicator to disappear
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".dataTables_processing")))
            
            # Additional wait for rows to populate
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable tbody tr")))
            
            # Small buffer
            time.sleep(2)
            return True
            
        except TimeoutException:
            print("⚠ Timeout waiting for table to load")
            return False
    
    def scrape_player_stats(self, gameweek=None):
        """
        Scrape player stats for a specific gameweek.
        
        Args:
            gameweek: Gameweek number (None for overall)
            
        Returns:
            pandas DataFrame
        """
        if not self.logged_in:
            raise Exception("Not logged in. Call login() first.")
        
        # Construct URL
        if gameweek:
            url = f"{self.base_url}/player-stats/all-players/?gw={gameweek}"
            print(f"\nScraping Gameweek {gameweek}...")
        else:
            url = f"{self.base_url}/player-stats/all-players/"
            print("\nScraping overall player stats...")
        
        self.driver.get(url)
        
        # Wait for table to load
        if not self.wait_for_table_load():
            print("⚠ Warning: Table may not be fully loaded")
        
        # Extract table data
        try:
            table = self.driver.find_element(By.CSS_SELECTOR, "table.dataTable")
            
            # Get headers
            headers = []
            thead = table.find_element(By.TAG_NAME, "thead")
            header_cells = thead.find_elements(By.TAG_NAME, "th")
            
            for th in header_cells:
                text = th.text.strip()
                if text and text not in ['', ' ']:
                    headers.append(text)
            
            # Get rows
            tbody = table.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            
            data = []
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                row_data = [cell.text.strip() for cell in cells]
                
                # Only add rows with data
                if any(row_data):
                    data.append(row_data)
            
            # Remove first column if it's a checkbox/selection column
            if headers and headers[0] in ['Select', '', ' ', '☐']:
                headers = headers[1:]
                data = [row[1:] if len(row) > 1 else row for row in data]
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # Add metadata
            df['Gameweek'] = gameweek if gameweek else 'Overall'
            df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"✓ Extracted {len(df)} players")
            return df
            
        except NoSuchElementException:
            print("✗ Could not find table on page")
            raise
    
    def scrape_custom_table(self, table_id):
        """
        Scrape a custom My Stats Table by ID.
        
        Args:
            table_id: The table ID from the URL (e.g., 66933)
            
        Returns:
            pandas DataFrame
        """
        if not self.logged_in:
            raise Exception("Not logged in. Call login() first.")
        
        url = f"{self.base_url}/my-stats-tables/view/{table_id}/"
        print(f"\nScraping custom table {table_id}...")
        
        self.driver.get(url)
        
        if not self.wait_for_table_load():
            print("⚠ Warning: Table may not be fully loaded")
        
        # Try to find gameweek selector
        try:
            gw_select = self.driver.find_element(By.ID, "gw-select")
            options = gw_select.find_elements(By.TAG_NAME, "option")
            gameweeks = [opt.get_attribute("value") for opt in options if opt.get_attribute("value")]
            print(f"✓ Found {len(gameweeks)} gameweeks available")
            return gameweeks
        except:
            print("⚠ Could not find gameweek selector")
            return []
    
    def scrape_custom_table_all_gameweeks(self, table_id, gameweeks=None, delay=2):
        """
        Scrape custom table for multiple gameweeks.
        
        Args:
            table_id: The table ID
            gameweeks: List of gameweek numbers (None to auto-detect)
            delay: Seconds between requests
            
        Returns:
            Combined DataFrame
        """
        all_data = []
        
        # If gameweeks not provided, detect them
        if gameweeks is None:
            base_url = f"{self.base_url}/my-stats-tables/view/{table_id}/"
            self.driver.get(base_url)
            self.wait_for_table_load()
            
            try:
                # Try to find gameweek options
                gw_elements = self.driver.find_elements(By.CSS_SELECTOR, "select#gameweek option, select[name='gw'] option")
                if gw_elements:
                    gameweeks = [opt.get_attribute("value") for opt in gw_elements if opt.get_attribute("value")]
                    gameweeks = [int(gw) for gw in gameweeks if gw.isdigit()]
                    print(f"✓ Auto-detected gameweeks: {gameweeks}")
            except:
                print("⚠ Could not auto-detect gameweeks. Provide them manually.")
                return None
        
        # Scrape each gameweek
        for gw in gameweeks:
            try:
                url = f"{self.base_url}/my-stats-tables/view/{table_id}/?gw={gw}"
                print(f"\nFetching GW{gw}...")
                
                self.driver.get(url)
                self.wait_for_table_load()
                
                # Extract table
                table = self.driver.find_element(By.CSS_SELECTOR, "table.dataTable")
                
                # Headers
                headers = []
                thead = table.find_element(By.TAG_NAME, "thead")
                header_cells = thead.find_elements(By.TAG_NAME, "th")
                for th in header_cells:
                    text = th.text.strip()
                    if text:
                        headers.append(text)
                
                # Rows
                tbody = table.find_element(By.TAG_NAME, "tbody")
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                
                data = []
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    row_data = [cell.text.strip() for cell in cells]
                    if any(row_data):
                        data.append(row_data)
                
                # Clean up headers/data
                if headers and headers[0] in ['Select', '', ' ', '☐']:
                    headers = headers[1:]
                    data = [row[1:] if len(row) > 1 else row for row in data]
                
                df = pd.DataFrame(data, columns=headers)
                df['Gameweek'] = gw
                df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                all_data.append(df)
                print(f"✓ GW{gw}: {len(df)} rows")
                
                if gw != gameweeks[-1]:
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"✗ Error fetching GW{gw}: {str(e)}")
                continue
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"\n✓ Total rows: {len(combined)}")
            return combined
        return None
    
    def scrape_multiple_gameweeks(self, start_gw, end_gw, delay=2):
        """Scrape player stats for multiple gameweeks."""
        all_data = []
        
        for gw in range(start_gw, end_gw + 1):
            try:
                df = self.scrape_player_stats(gameweek=gw)
                all_data.append(df)
                
                if gw < end_gw:
                    print(f"Waiting {delay}s...")
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"✗ Error with GW{gw}: {str(e)}")
                continue
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            print(f"\n✓ Total rows: {len(combined)}")
            return combined
        return None
    
    def save_to_csv(self, df, filename=None):
        """Save DataFrame to CSV."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ffs_data_{timestamp}.csv"
        
        output_dir = Path("ffs_data")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"\n✓ Saved to: {filepath}")
        return filepath
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            print("✓ Browser closed")


def get_credentials():
    """Get credentials from environment or prompt."""
    username = os.getenv('FFS_USERNAME')
    password = os.getenv('FFS_PASSWORD')
    
    if not username or not password:
        print("\n" + "="*60)
        print("CREDENTIALS SETUP")
        print("="*60)
        if not username:
            username = input("Email/Username: ").strip()
        if not password:
            password = getpass("Password (hidden): ")
        print("="*60 + "\n")
    
    return username, password


# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    try:
        username, password = get_credentials()
        
        if not username or not password:
            print("✗ Username and password required!")
            exit(1)
        
        # Initialize scraper
        scraper = FFScoutSeleniumScraper(
            username=username,
            password=password,
            headless=True  # Set to False to see the browser
        )
        
        # Login
        if scraper.login():
            print("\n" + "="*60)
            print("CHOOSE YOUR SCRAPING TASK")
            print("="*60)
            
            # ============================================================
            # OPTION 1: Scrape standard player stats for multiple GWs
            # ============================================================
            print("\nOption 1: Standard Player Stats")
            START_GW = 1
            END_GW = 10  # Adjust to current gameweek
            
            df_standard = scraper.scrape_multiple_gameweeks(START_GW, END_GW, delay=2)
            if df_standard is not None:
                scraper.save_to_csv(df_standard, f"player_stats_gw{START_GW}_{END_GW}.csv")
            
            # ============================================================
            # OPTION 2: Scrape YOUR CUSTOM TABLE (table ID 66933)
            # ============================================================
            print("\n\nOption 2: Custom My Stats Table")
            TABLE_ID = 66933  # Your table ID
            GAMEWEEKS = list(range(1, 11))  # GW 1-10, adjust as needed
            
            df_custom = scraper.scrape_custom_table_all_gameweeks(
                table_id=TABLE_ID,
                gameweeks=GAMEWEEKS,
                delay=2
            )
            
            if df_custom is not None:
                scraper.save_to_csv(df_custom, f"custom_table_{TABLE_ID}_master.csv")
            
            print("\n" + "="*60)
            print("✓ SCRAPING COMPLETE!")
            print("="*60)
            
        else:
            print("✗ Login failed")
        
    except KeyboardInterrupt:
        print("\n\n✗ Cancelled by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'scraper' in locals():
            scraper.close()