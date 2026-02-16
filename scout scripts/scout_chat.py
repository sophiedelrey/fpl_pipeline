import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

# -------------------- Ρυθμίσεις --------------------
USERNAME = "ritaras4"
PASSWORD = "FSUfpldata!"
SEASON = "2024-25"
GAMEWEEKS = list(range(1, 39))  # πχ Gameweeks 1-38
OUTPUT_FILE = "ffs_all_players_timeseries.csv"

# -------------------- Εκκίνηση browser --------------------
options = webdriver.FirefoxOptions()
# options.add_argument("--headless")  # Αφαίρεσε το σχόλιο για να τρέξει headless
driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

# -------------------- Login --------------------
driver.get("https://members.fantasyfootballscout.co.uk/login/")
wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
driver.find_element(By.ID, "password").send_keys(PASSWORD)
driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

# Περιμένουμε να εμφανιστεί στοιχείο που δείχνει επιτυχημένο login
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".member-area")))

# -------------------- Πλοήγηση στη σελίδα Stats --------------------
driver.get("https://members.fantasyfootballscout.co.uk/player-stats/all-players/")
wait.until(EC.presence_of_element_located((By.CLASS_NAME, "stats")))

all_data = []

for gw in GAMEWEEKS:
    print(f"Fetching Gameweek {gw}...")

    # -------------------- Φιλτράρισμα Season και GW --------------------
    season_select = Select(driver.find_element(By.NAME, "season"))
    season_select.select_by_visible_text(SEASON)
    
    range_from = Select(driver.find_element(By.NAME, "range_from"))
    range_from.select_by_value(str(gw))
    range_to = Select(driver.find_element(By.NAME, "range_to"))
    range_to.select_by_value(str(gw))
    
    driver.find_element(By.ID, "apply_filters").click()  # Κουμπί Apply
    time.sleep(1)  # Μικρό pause για JS reload

    # Περιμένουμε να φορτώσει ο πίνακας
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "stats")))
    
    table = driver.find_element(By.CLASS_NAME, "stats")
    rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Παίρνουμε μόνο data rows

    for row in rows:
        cols = [td.text for td in row.find_elements(By.TAG_NAME, "td")]
        if cols:  # Αποφυγή κενών γραμμών
            all_data.append([gw] + cols)

# -------------------- Αποθήκευση CSV --------------------
columns = ["Gameweek", "Name", "Team", "Cost", "App", "Starts", "Mins", "On", "Off", "M/App", "M/Strt",
           "G", "A", "CS", "GC", "OG", "PS", "Svs", "YC", "RC", "sBln", "ARtn", "Rtn", "DC", "B", "DD", "Tot",
           "M/Pt", "Pts/Strt"]
df = pd.DataFrame(all_data, columns=columns)
df.to_csv(OUTPUT_FILE, index=False)
print(f"Saved CSV to {OUTPUT_FILE}")

driver.quit()

