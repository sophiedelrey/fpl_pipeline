import pandas as pd

# === CONFIG ===
FILE_PATH = "output/training_data.csv"

print(f"Loading: {FILE_PATH}")
df = pd.read_csv(FILE_PATH, encoding="utf-8-sig")

# Εντοπισμός κενών τιμών στη Position
missing_mask = df["Position"].isna() | (df["Position"] == "") | (df["Position"].astype(str).str.strip() == "")

missing_rows = df[missing_mask]

print("\n==============================================")
print("🔍 CHECKING COLUMN: Position")
print("==============================================")

print(f"Total rows: {len(df):,}")
print(f"Empty Position rows: {missing_rows.shape[0]:,}")

if missing_rows.shape[0] == 0:
    print("\n✅ No missing Position values found!")
else:
    print("\n⚠️ Missing Position values found!")
    print("Showing first 20 problematic rows:\n")
    print(missing_rows.head(20))
    
    # Stats για να καταλάβεις από πού προέρχεται το πρόβλημα
    print("\n📌 Missing by season:")
    print(missing_rows["season"].value_counts())

    print("\n📌 Missing by Player Name:")
    print(missing_rows["Player Name"].value_counts().head(10))
