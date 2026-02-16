import requests
from bs4 import BeautifulSoup
import os
from getpass import getpass

# Get credentials
username = os.getenv('FFS_USERNAME') or input("Email/Username: ").strip()
password = os.getenv('FFS_PASSWORD') or getpass("Password (hidden): ")

# Create session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
})

# Login
print("Logging in...")
main_site = "https://www.fantasyfootballscout.co.uk"
login_page = session.get(f"{main_site}/my-account/")
soup = BeautifulSoup(login_page.content, 'html.parser')

login_data = {
    'log': username,
    'pwd': password,
    'rememberme': 'forever',
    'wp-submit': 'Log In',
}

form = soup.find('form', {'id': 'loginform'}) or soup.find('form', {'name': 'loginform'})
if form:
    hidden = form.find_all('input', {'type': 'hidden'})
    for h in hidden:
        if h.get('name'):
            login_data[h.get('name')] = h.get('value')

session.post(f"{main_site}/wp-login.php", data=login_data, allow_redirects=True)
print("✓ Login attempted")

# Fetch the player stats page
print("\nFetching player stats page for GW1...")
url = "https://members.fantasyfootballscout.co.uk/player-stats/all-players/?gw=1"
response = session.get(url)

# Save the HTML
with open('ffs_page_gw1.html', 'w', encoding='utf-8') as f:
    f.write(response.text)

print(f"✓ Page saved to: ffs_page_gw1.html")
print(f"✓ Status code: {response.status_code}")
print(f"\nNow let's analyze the structure...")

# Parse and look for tables
soup = BeautifulSoup(response.text, 'html.parser')

# Find all tables
tables = soup.find_all('table')
print(f"\n Found {len(tables)} table(s) in the page")

for i, table in enumerate(tables):
    print(f"\n--- Table {i+1} ---")
    print(f"Classes: {table.get('class')}")
    print(f"ID: {table.get('id')}")
    
    # Check for data attributes (DataTables often use these)
    for attr in table.attrs:
        if 'data' in attr:
            print(f"{attr}: {table.get(attr)}")

# Look for script tags that might initialize DataTables
print("\n\n=== Looking for DataTable initialization scripts ===")
scripts = soup.find_all('script')
for script in scripts:
    if script.string and ('DataTable' in script.string or 'dataTable' in script.string):
        print("\nFound DataTable script:")
        # Print first 500 chars
        print(script.string[:500])
        print("...\n")

print("\n✓ Debug complete! Check the output above.")
print("Also open 'ffs_page_gw1.html' in a text editor to inspect the full HTML.")