import os
import time
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException
)

# === CONFIG ===
USERNAME = "ritaras4"
PASSWORD = "FSUfpldata!"
BASE_URL = "https://members.fantasyfootballscout.co.uk"
TARGET_STATS_PATH = "/my-stats-tables/view/66933/"  # Use your actual table ID from the URL
OUT_DIR = Path("data/fpl_scout/2024-25")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "ffs_mystats_table_gw_2024-25.csv"

HEADLESS = False
WAIT_LONG = 20
WAIT_SHORT = 4

# === FUNCTIONS ===

def start_driver(headless=HEADLESS):
    options = webdriver.FirefoxOptions()
    if headless:
        options.headless = True
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.maximize_window()
    return driver

def try_accept_cookies(driver):
    """Try to accept cookies if dialog appears."""
    xpaths = [
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'allow')]",
        "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]"
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            time.sleep(0.4)
            return True
        except Exception:
            continue
    return False

def login(driver):
    """Login to the site."""
    possible_login_paths = [
        "/my-account/",
        "/login/",
        "/wp-login.php",
        "/member-login/",
        "/"
    ]
    for p in possible_login_paths:
        try:
            driver.get(BASE_URL + p)
            time.sleep(1)
            try_accept_cookies(driver)

            username_inputs = driver.find_elements(By.XPATH,
                "//input[@name='username' or @name='user' or @name='email' or contains(@id,'user') or contains(@id,'email') or contains(@placeholder,'Email') or contains(@placeholder,'Username')]")
            pwd_inputs = driver.find_elements(By.XPATH,
                "//input[@type='password' or @name='password' or contains(@id,'pass')]")

            if username_inputs and pwd_inputs:
                username_inputs[0].clear()
                username_inputs[0].send_keys(USERNAME)
                pwd_inputs[0].clear()
                pwd_inputs[0].send_keys(PASSWORD)

                try:
                    submit_btn = driver.find_element(By.XPATH,
                        "//button[@type='submit' or contains(.,'Log in') or contains(.,'Login') or contains(.,'Sign in')]")
                    submit_btn.click()
                except NoSuchElementException:
                    pwd_inputs[0].send_keys("\n")
                
                WebDriverWait(driver, WAIT_LONG).until(
                    lambda d: d.current_url != BASE_URL + p
                )
                return True
        except Exception:
            continue
    
    # Try clicking login link
    try:
        driver.get(BASE_URL)
        try_accept_cookies(driver)
        login_link_xp = "//a[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'log in') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login') or contains(.,'Sign in')]"
        links = driver.find_elements(By.XPATH, login_link_xp)
        if links:
            links[0].click()
            time.sleep(1)
            username_inputs = driver.find_elements(By.XPATH,
                "//input[@name='username' or @name='user' or @name='email' or contains(@id,'user') or contains(@id,'email')]")
            pwd_inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
            if username_inputs and pwd_inputs:
                username_inputs[0].send_keys(USERNAME)
                pwd_inputs[0].send_keys(PASSWORD)
                pwd_inputs[0].send_keys("\n")
                WebDriverWait(driver, WAIT_LONG).until(lambda d: d.current_url != BASE_URL)
                return True
    except Exception:
        pass
    return False

def set_filters_and_click_filter(driver, gw):
    """Set Season=2024/25, Range=Gameweek Range, From=gw, To=gw and click FILTER."""
    wait = WebDriverWait(driver, WAIT_LONG)
    wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(.,'Season')]")))

    try:
        season_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'Season')]/following::select[1]"))
        range_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'Range')]/following::select[1]"))
        from_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'From')]/following::select[1]"))
        to_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'To')]/following::select[1]"))

        # Set Season
        for season_txt in ("2024/25", "2024-25", "2024"):
            try:
                season_sel.select_by_visible_text(season_txt)
                break
            except Exception:
                pass

        # Set Range to Gameweek Range
        for rtxt in ("Gameweek Range", "Gameweek range", "Gameweek"):
            try:
                range_sel.select_by_visible_text(rtxt)
                break
            except Exception:
                pass

        # Set From and To
        from_sel.select_by_visible_text(str(gw))
        to_sel.select_by_visible_text(str(gw))

    except Exception as e:
        print(f"Warning: normal Select failed, trying JS fallback: {e}")
        js = f"""
        (function(){{
            function setSelectByLabel(labelText, value) {{
                var lbl = Array.from(document.querySelectorAll('label')).find(l => l.innerText.trim().includes(labelText));
                if (!lbl) return false;
                var sel = lbl.nextElementSibling;
                if (!sel) sel = lbl.parentElement.querySelector('select');
                if (!sel) return false;
                sel.value = value;
                sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            setSelectByLabel('Season','2024/25') || setSelectByLabel('Season','2024-25');
            setSelectByLabel('Range','Gameweek Range') || setSelectByLabel('Range','Gameweek');
            setSelectByLabel('From','{gw}');
            setSelectByLabel('To','{gw}');
        }})();"""
        driver.execute_script(js)
        time.sleep(0.6)

    # Click FILTER button
    filter_btn_candidates = driver.find_elements(By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter') or contains(.,'FILTER')]")
    if filter_btn_candidates:
        try:
            filter_btn_candidates[0].click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].scrollIntoView(true);", filter_btn_candidates[0])
            time.sleep(0.2)
            filter_btn_candidates[0].click()
    else:
        driver.execute_script("""
            var b = Array.from(document.querySelectorAll('button')).find(x=>/filter/i.test(x.innerText));
            if(b) b.click();
        """)
    time.sleep(2)  # Wait for table to reload


def scrape_table_to_df(driver):
    """Extract table with proper header handling."""
    wait = WebDriverWait(driver, WAIT_LONG)
    
    try:
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
    except TimeoutException:
        raise RuntimeError("Timed out waiting for table to appear.")

    # === EXTRACT HEADERS ===
    headers = []
    try:
        thead = table.find_element(By.TAG_NAME, "thead")
        header_rows = thead.find_elements(By.TAG_NAME, "tr")
        
        # Get the last header row (most specific column names)
        if header_rows:
            ths = header_rows[-1].find_elements(By.TAG_NAME, "th")
            headers = [th.text.strip() for th in ths]
            # Remove empty headers (checkboxes, etc.)
            headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
    except Exception as e:
        print(f"Warning: header extraction failed: {e}")
        headers = []

    # === EXTRACT ROWS ===
    rows = []
    tbody_trs = table.find_elements(By.CSS_SELECTOR, "tbody tr")
    for tr in tbody_trs:
        if not tr.is_displayed():
            continue
        cells = tr.find_elements(By.CSS_SELECTOR, "td")
        row = [c.text.strip() for c in cells]
        if any(cell != "" for cell in row):
            rows.append(row)

    # Generate headers if extraction failed
    if not headers and rows:
        max_cols = max((len(r) for r in rows), default=0)
        headers = [f"col_{i}" for i in range(max_cols)]

    # Normalize row lengths
    norm_rows = []
    for r in rows:
        if len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        elif len(r) > len(headers):
            extra = len(r) - len(headers)
            for i in range(extra):
                headers.append(f"col_extra_{i}")
        norm_rows.append(r)

    df = pd.DataFrame(norm_rows, columns=headers)
    
    # Remove checkbox column if it exists
    if 'col_0' in df.columns and df['col_0'].str.strip().eq('').all():
        df = df.drop(columns=['col_0'])
    
    return df


# === MAIN FLOW ===
def main():
    driver = start_driver()
    try:
        driver.get(BASE_URL)
        try_accept_cookies(driver)

        print("Logging in...")
        ok = login(driver)
        if not ok:
            print("Warning: login flow failed. Attempting to continue...")

        stats_url = BASE_URL.rstrip("/") + TARGET_STATS_PATH
        print(f"Opening My Stats Table: {stats_url}")
        driver.get(stats_url)
        try_accept_cookies(driver)
        time.sleep(2)

        all_dfs = []
        for gw in range(1, 39):
            print(f"\n=== Processing Gameweek {gw} ===")
            WebDriverWait(driver, WAIT_LONG).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            try:
                set_filters_and_click_filter(driver, gw)
            except Exception as e:
                print(f"Failed to set filters for GW {gw}: {e}")
                driver.get(stats_url)
                time.sleep(2)
                set_filters_and_click_filter(driver, gw)

            try:
                WebDriverWait(driver, WAIT_LONG).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tbody tr")) > 0
                )
            except TimeoutException:
                print(f"Warning: table rows didn't appear for GW {gw}")

            df = scrape_table_to_df(driver)
            df.insert(0, "gameweek", gw)
            print(f"Scraped {len(df)} rows for GW {gw}")
            print(f"Columns: {list(df.columns)}")
            all_dfs.append(df)

            time.sleep(1)

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True, sort=False)
            combined.to_csv(OUT_CSV, index=False)
            print(f"\n✓ Saved {len(combined)} total rows to: {OUT_CSV.resolve()}")
            print(f"✓ Columns in CSV: {list(combined.columns)}")
        else:
            print("No dataframes collected.")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()