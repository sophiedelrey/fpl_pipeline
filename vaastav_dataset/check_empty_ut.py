import os
import pandas as pd

DATA_ROOT = "data"

print("\n=== FPL CSV Check: UTF-8 & Empty Files ===\n")

for root, _, files in os.walk(DATA_ROOT):
    for file in files:
        if file.endswith(".csv"):
            path = os.path.join(root, file)
            # Έλεγχος UTF-8
            try:
                with open(path, "r", encoding="utf-8") as f:
                    f.read()
                utf8_ok = True
            except UnicodeDecodeError:
                utf8_ok = False

            # Έλεγχος empty CSV
            empty_csv = False
            if utf8_ok:
                try:
                    df = pd.read_csv(path, encoding="utf-8")
                    if df.empty:
                        empty_csv = True
                except Exception as e:
                    print(f"❌ ERROR reading {path}: {e}")
                    continue

            # Εκτύπωση αποτελεσμάτων
            status = []
            if utf8_ok:
                status.append("UTF-8 OK")
            else:
                status.append("NOT UTF-8")
            if empty_csv:
                status.append("EMPTY CSV")

            print(f"{path}: {', '.join(status)}")

print("\n=== Check Complete ===\n")
