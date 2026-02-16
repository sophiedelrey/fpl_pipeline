import pandas as pd

df = pd.read_csv("output/training_data.csv", encoding="utf-8-sig")

TEAM = "Man City"   # βάλε εδώ την ομάδα για διάγνωση

subset = df[df["Player Team Name"] == TEAM][
    ["season", "Gameweek", "Player Team Name", "Opponent Name", "Is Home", "Opponent Difficulty"]
]

print("\n=== SAMPLE ROWS ===")
print(subset.head(15))

# 1. Check average difficulty per Opponent
opponent_stats = subset.groupby("Opponent Name")["Opponent Difficulty"].agg(["min", "max", "mean", "count"]).sort_values("mean")
print("\n=== OPPONENT-BASED DIFFICULTY FOR", TEAM, "===")
print(opponent_stats)

# 2. Check differences Home vs Away
home = subset[subset["Is Home"] == True]["Opponent Difficulty"].mean()
away = subset[subset["Is Home"] == False]["Opponent Difficulty"].mean()

print("\n=== HOME vs AWAY difficulty ===")
print(f"Home mean difficulty: {home:.2f}")
print(f"Away mean difficulty: {away:.2f}")

# 3. Show suspicious cases
print("\n=== CHECK FOR CASES WHERE TEAM PLAYS VS CITY ===")
cases = df[df["Opponent Name"] == TEAM][["Player Team Name","Opponent Name","Opponent Difficulty","season","Gameweek"]]
print(cases.head(20))
