import pandas as pd

# Διαδρομή προς το training_data.csv
input_path = "output/training_data.csv"

# Φόρτωσε το αρχείο
df = pd.read_csv(input_path)

# Εμφάνισε τις διαθέσιμες σεζόν για έλεγχο
print("Διαθέσιμες seasons:", df['season'].unique())

# Φίλτραρε ώστε να αφαιρέσεις τη σεζόν 2016-17
df_filtered = df[df["season"] != "2016-17"]

# Εμφάνισε πόσες γραμμές αφαιρέθηκαν
removed = len(df) - len(df_filtered)
print(f"Διαγράφηκαν {removed} γραμμές με season = 2016-17")

# Αποθήκευση πίσω στο ίδιο αρχείο
df_filtered.to_csv(input_path, index=False)
print("✅ Το αρχείο ενημερώθηκε επιτυχώς χωρίς τη σεζόν 2016-17.")
