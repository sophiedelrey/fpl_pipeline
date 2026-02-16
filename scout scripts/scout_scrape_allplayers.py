import os
import time
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException
)

# === CONFIG ===
USERNAME = "ritaras4"
PASSWORD = "FSUfpldata!"
BASE_URL = "https://members.fantasyfootballscout.co.uk"
TARGET_STATS_PATH = "/player-stats/all-players/"
OUT_DIR = Path("data/fpl_scout")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT_DIR / "test_scout.csv"

HEADLESS = False  # Set to False for testing/reliability
WAIT_LONG = 20   # Keep original for reliability
WAIT_SHORT = 3   # Balanced wait time
TEST_MODE = True  # Set to False to run all 38 gameweeks
MAX_GAMEWEEK = 5  # Only used when TEST_MODE is True

# === FUNCTIONS ===

def start_driver(headless=HEADLESS):
    options = webdriver.FirefoxOptions()
    if headless:
        options.headless = True
    # Performance optimizations
    options.set_preference("network.http.pipelining", True)
    options.set_preference("network.http.proxy.pipelining", True)
    options.set_preference("network.http.pipelining.maxrequests", 8)
    options.set_preference("browser.cache.disk.enable", True)
    options.set_preference("browser.cache.memory.enable", True)
    
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    if not headless:
        driver.maximize_window()
    return driver

def try_accept_cookies(driver):
    """Try to accept cookies if dialog appears."""
    xpaths = [
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'accept')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'agree')]",
        "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'allow')]",
    ]
    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click()
            time.sleep(0.3)
            return True
        except Exception:
            continue
    return False

def login(driver):
    """Login to the site."""
    possible_login_paths = ["/my-account/", "/login/", "/wp-login.php"]
    
    for p in possible_login_paths:
        try:
            driver.get(BASE_URL + p)
            time.sleep(1)
            try_accept_cookies(driver)

            username_inputs = driver.find_elements(By.XPATH,
                "//input[@name='username' or @name='user' or @name='email' or contains(@id,'user') or contains(@id,'email')]")
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
    
    return False

def get_table_signature(driver):
    """Get a unique signature from the table to detect changes."""
    try:
        first_row = driver.find_element(By.CSS_SELECTOR, "table tbody tr:first-child")
        cells = first_row.find_elements(By.CSS_SELECTOR, "td")
        signature = "_".join([c.text.strip() for c in cells[:8]])  # More cells for reliability
        return signature
    except:
        return None

def force_click_filter_button(driver):
    """Try multiple methods to click the filter button."""
    
    print(f"  🔘 Attempting to click FILTER button...")
    
    # First, let's see what buttons exist on the page
    try:
        all_buttons_info = driver.execute_script("""
            return Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"], a.button, .button'))
                .map(b => ({
                    tag: b.tagName,
                    text: (b.innerText || b.value || b.textContent || '').trim().substring(0, 50),
                    id: b.id || '',
                    class: b.className || '',
                    type: b.type || ''
                }));
        """)
        print(f"  📋 Found {len(all_buttons_info)} button-like elements on page:")
        for i, btn_info in enumerate(all_buttons_info[:10]):  # Show first 10
            print(f"     {i+1}. {btn_info['tag']} - text:'{btn_info['text']}' id:'{btn_info['id']}' class:'{btn_info['class']}'")
    except Exception as e:
        print(f"  ⚠ Could not list buttons: {e}")
    
    # Method 1: Find by text (case insensitive)
    try:
        filter_btn = driver.find_element(By.XPATH, 
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter')]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_btn)
        time.sleep(0.3)
        filter_btn.click()
        print(f"  ✓ Method 1: Normal click successful")
        return True
    except ElementClickInterceptedException:
        print(f"  ⚠ Method 1: Click intercepted")
    except Exception as e:
        print(f"  ⚠ Method 1: Failed - {type(e).__name__}")
    
    # Method 2: Try input buttons with filter text
    try:
        filter_inputs = driver.find_elements(By.XPATH, 
            "//input[@type='submit' or @type='button'][contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter')]")
        if filter_inputs:
            filter_inputs[0].click()
            print(f"  ✓ Method 2: Input button click successful")
            return True
    except Exception as e:
        print(f"  ⚠ Method 2: Failed - {type(e).__name__}")
    
    # Method 3: Try any button/link with "filter" in various attributes
    try:
        filter_btn = driver.find_element(By.XPATH, 
            "//*[contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter') or "
            "contains(translate(@title,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter') or "
            "contains(translate(@aria-label,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter') or "
            "contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter')]")
        driver.execute_script("arguments[0].click();", filter_btn)
        print(f"  ✓ Method 3: Attribute search click successful")
        return True
    except Exception as e:
        print(f"  ⚠ Method 3: Failed - {type(e).__name__}")
    
    # Method 4: ActionChains click
    try:
        filter_btn = driver.find_element(By.XPATH, 
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter')]")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", filter_btn)
        time.sleep(0.3)
        actions = ActionChains(driver)
        actions.move_to_element(filter_btn).click().perform()
        print(f"  ✓ Method 4: ActionChains click successful")
        return True
    except Exception as e:
        print(f"  ⚠ Method 4: Failed - {type(e).__name__}")
    
    # Method 5: JavaScript click
    try:
        filter_btn = driver.find_element(By.XPATH, 
            "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'filter')]")
        driver.execute_script("arguments[0].click();", filter_btn)
        print(f"  ✓ Method 5: JavaScript click successful")
        return True
    except Exception as e:
        print(f"  ⚠ Method 5: Failed - {type(e).__name__}")
    
    # Method 6: Pure JavaScript selector
    try:
        result = driver.execute_script("""
            var buttons = Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'));
            var filterBtn = buttons.find(b => /filter/i.test(b.innerText || b.value || b.textContent));
            if (filterBtn) {
                filterBtn.click();
                return true;
            }
            return false;
        """)
        if result:
            print(f"  ✓ Method 6: Pure JS click successful")
            return True
        else:
            print(f"  ⚠ Method 6: Filter button not found in DOM")
    except Exception as e:
        print(f"  ⚠ Method 6: Failed - {type(e).__name__}")
    
    # Method 7: Try form submit
    try:
        form = driver.find_element(By.XPATH, "//form[.//select]")
        driver.execute_script("arguments[0].submit();", form)
        print(f"  ✓ Method 7: Form submit successful")
        return True
    except Exception as e:
        print(f"  ⚠ Method 7: Failed - {type(e).__name__}")
    
    print(f"  ✗ ALL METHODS FAILED - Could not click filter button!")
    return False

def set_filters_and_click_filter(driver, gw):
    """Set Season=2024/25, Range=Gameweek Range, From=gw, To=gw and click FILTER."""
    wait = WebDriverWait(driver, WAIT_LONG)
    wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(.,'Season')]")))

    old_signature = get_table_signature(driver)
    print(f"  Old signature: {old_signature[:50] if old_signature else 'None'}...")

    # Try standard Selenium Select first for reliability
    try:
        season_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'Season')]/following::select[1]"))
        range_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'Range')]/following::select[1]"))
        from_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'From')]/following::select[1]"))
        to_sel = Select(driver.find_element(By.XPATH, "//label[contains(.,'To')]/following::select[1]"))

        # Set Season
        for season_txt in ("2024/25", "2024-25", "2024"):
            try:
                season_sel.select_by_visible_text(season_txt)
                print(f"  ✓ Set Season: {season_txt}")
                break
            except Exception:
                pass

        # Set Range
        for rtxt in ("Gameweek Range", "Gameweek range", "Gameweek"):
            try:
                range_sel.select_by_visible_text(rtxt)
                print(f"  ✓ Set Range: {rtxt}")
                break
            except Exception:
                pass

        # Set From and To
        from_sel.select_by_visible_text(str(gw))
        print(f"  ✓ Set From: {gw}")
        
        to_sel.select_by_visible_text(str(gw))
        print(f"  ✓ Set To: {gw}")
        
        time.sleep(0.5)

    except Exception as e:
        print(f"  ⚠ Standard Select failed: {type(e).__name__}")
        print(f"  ⚠ Trying JavaScript fallback...")
        
        # JavaScript fallback
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
            var r1 = setSelectByLabel('Season','2024/25') || setSelectByLabel('Season','2024-25');
            var r2 = setSelectByLabel('Range','Gameweek Range') || setSelectByLabel('Range','Gameweek');
            var r3 = setSelectByLabel('From','{gw}');
            var r4 = setSelectByLabel('To','{gw}');
            return {{season: r1, range: r2, from: r3, to: r4}};
        }})();"""
        result = driver.execute_script(js)
        print(f"  JS result: {result}")
        time.sleep(0.5)

    # Click filter button
    click_success = force_click_filter_button(driver)
    
    if not click_success:
        print(f"  ⚠⚠ WARNING: Failed to click filter button!")
        return False
    
    # Wait for table to update
    print(f"  ⏳ Waiting for table to update...")
    time.sleep(1.5)
    
    # Look for loading indicators
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 
                ".loading, .spinner, [class*='load'], .dataTables_processing"))
        )
        print(f"  ⏳ Loading indicator detected...")
        WebDriverWait(driver, WAIT_LONG).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, 
                ".loading, .spinner, [class*='load'], .dataTables_processing"))
        )
        print(f"  ✓ Loading complete")
    except TimeoutException:
        pass
    
    # Wait for signature change
    max_wait = 15
    start_time = time.time()
    checks = 0
    
    while (time.time() - start_time) < max_wait:
        time.sleep(1)
        checks += 1
        new_signature = get_table_signature(driver)
        
        if new_signature and new_signature != old_signature:
            elapsed = time.time() - start_time
            print(f"  ✓✓ TABLE UPDATED! (after {elapsed:.1f}s, {checks} checks)")
            print(f"  New signature: {new_signature[:50]}...")
            time.sleep(0.5)
            return True
        
        if checks % 3 == 0:
            print(f"  ⏳ Still waiting... ({checks} checks)")
    
    print(f"  ⚠⚠ WARNING: Table did NOT update after {max_wait}s!")
    print(f"  Old: {old_signature[:50] if old_signature else 'None'}")
    print(f"  New: {new_signature[:50] if new_signature else 'None'}")
    return False

def scrape_table_to_df(driver):
    """Extract table with proper multi-level header handling."""
    wait = WebDriverWait(driver, WAIT_LONG)
    
    try:
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable, table.wp-list-table, table")))
    except TimeoutException:
        raise RuntimeError("Timed out waiting for table to appear.")

    # === EXTRACT HEADERS ===
    headers = []
    try:
        thead = table.find_element(By.TAG_NAME, "thead")
        header_rows = thead.find_elements(By.TAG_NAME, "tr")
        
        if len(header_rows) >= 2:
            top_row = header_rows[0]
            bottom_row = header_rows[1]
            
            top_ths = top_row.find_elements(By.TAG_NAME, "th")
            bottom_ths = bottom_row.find_elements(By.TAG_NAME, "th")
            
            col_idx = 0
            for top_th in top_ths:
                colspan = int(top_th.get_attribute("colspan") or 1)
                for i in range(colspan):
                    if col_idx < len(bottom_ths):
                        col_name = bottom_ths[col_idx].text.strip()
                        headers.append(col_name if col_name else f"col_{col_idx}")
                        col_idx += 1
        else:
            ths = header_rows[0].find_elements(By.TAG_NAME, "th")
            headers = [th.text.strip() for th in ths]
    except Exception:
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

    if not headers and rows:
        max_cols = max((len(r) for r in rows), default=0)
        headers = [f"col_{i}" for i in range(max_cols)]

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
            print("⚠ Warning: login flow failed. Attempting to continue...")

        stats_url = BASE_URL.rstrip("/") + TARGET_STATS_PATH
        print(f"Opening player stats: {stats_url}")
        driver.get(stats_url)
        try_accept_cookies(driver)
        time.sleep(2)

        all_dfs = []
        previous_signature = None
        
        # Determine how many gameweeks to scrape
        max_gw = MAX_GAMEWEEK if TEST_MODE else 38
        print(f"\n{'='*60}")
        print(f"TEST MODE: {'ENABLED' if TEST_MODE else 'DISABLED'}")
        print(f"Scraping gameweeks 1 to {max_gw}")
        print(f"{'='*60}\n")
        
        for gw in range(1, max_gw + 1):
            print(f"\n{'='*60}")
            print(f"=== GAMEWEEK {gw} ===")
            print(f"{'='*60}")
            
            WebDriverWait(driver, WAIT_LONG).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Set filters and click with retry logic
            success = False
            for attempt in range(3):  # Keep 3 attempts for reliability
                if attempt > 0:
                    print(f"\n  🔄 Retry attempt {attempt + 1}")
                    driver.get(stats_url)
                    time.sleep(2)
                
                success = set_filters_and_click_filter(driver, gw)
                
                if success:
                    break
                else:
                    print(f"  ⚠ Attempt {attempt + 1} failed")
                    time.sleep(1)
            
            if not success:
                print(f"  ✗✗ FAILED to update table for GW {gw} after 3 attempts!")
                print(f"  Skipping GW {gw}...")
                continue
            
            # Check for duplicate data
            current_signature = get_table_signature(driver)
            if previous_signature and current_signature == previous_signature:
                print(f"  ⚠⚠⚠ CRITICAL: Table data is IDENTICAL to previous GW!")
            
            # Scrape the table
            df = scrape_table_to_df(driver)
            df.insert(0, "gameweek", gw)
            
            # Print diagnostic info
            print(f"\n  ✓ Scraped {len(df)} rows for GW {gw}")
            if len(df) > 0:
                print(f"  First player: {df.iloc[0]['Name'] if 'Name' in df.columns else df.iloc[0, 1]}")
                print(f"  Sample stats: {list(df.iloc[0, 3:8].values)}")
            
            all_dfs.append(df)
            previous_signature = current_signature
            
            time.sleep(1)

        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True, sort=False)
            combined.to_csv(OUT_CSV, index=False)
            print(f"\n{'='*60}")
            print(f"✓✓ SUCCESS! Saved {len(combined)} total rows to:")
            print(f"  {OUT_CSV.resolve()}")
            print(f"\n✓ Columns: {list(combined.columns[:15])}...")
            
            # Show data distribution
            print(f"\n✓ Rows per gameweek:")
            gw_counts = combined['gameweek'].value_counts().sort_index()
            for gw, count in gw_counts.items():
                print(f"  GW {gw:2d}: {count:3d} rows")
            
            # Check for duplicates
            if len(gw_counts.unique()) == 1:
                print(f"\n✓✓ All gameweeks have the same row count ({gw_counts.iloc[0]}) - looks good!")
            else:
                print(f"\n⚠ Warning: Gameweeks have different row counts")
                
            if TEST_MODE:
                print(f"\n{'='*60}")
                print(f"🧪 TEST MODE: Successfully scraped {max_gw} gameweeks!")
                print(f"If results look good, set TEST_MODE = False to run all 38 gameweeks")
                print(f"{'='*60}")
        else:
            print("⚠ No dataframes collected.")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()





