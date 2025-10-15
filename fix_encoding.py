import os
import shutil

DATA_ROOT = "data"  # άλλαξέ το αν τα csv σου είναι αλλού

for root, _, files in os.walk(DATA_ROOT):
    for file in files:
        if file.endswith(".csv"):
            path = os.path.join(root, file)
            backup_path = path + ".bak"

            try:
                # Αν δεν υπάρχει ήδη backup, φτιάξτο
                if not os.path.exists(backup_path):
                    shutil.copy(path, backup_path)

                # Δοκίμασε να διαβάσεις ως UTF-8
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Αν αποτύχει, δοκίμασε με Latin-1
                    with open(path, "r", encoding="latin-1") as f:
                        content = f.read()

                # Ξαναγράψε το αρχείο σε UTF-8
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"Fixed: {path}")
            except Exception as e:
                print(f"Error fixing {path}: {e}")
