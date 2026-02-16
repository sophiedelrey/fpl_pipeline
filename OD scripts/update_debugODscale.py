import pandas as pd
from pathlib import Path

DATA_PATH = Path("output/training_data.csv")

# Teams generally EASY in most seasons
EASY_TEAMS = [
    "Sheffield Utd", "Burnley", "Luton", "Wolves", "Bournemouth",
    "Huddersfield", "Norwich", "Watford", "Cardiff"
]

# Teams generally HARD in most seasons
HARD_TEAMS = [
    "Man City", "Liverpool", "Arsenal", "Chelsea", "Man Utd", "Newcastle",
    "Tottenham"
]


def load_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training data not found: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    return df


def check_value_range(df):
    print("\n=== CHECK 1: Difficulty must be in [1, 5] ===")
    invalid = df[~df["Opponent Difficulty"].isin([1,2,3,4,5])]
    if len(invalid) == 0:
        print("OK: All values are within 1-5.")
    else:
        print("WARNING: Invalid difficulty values found:")
        print(invalid.head())


def check_means_per_season(df):
    print("\n=== CHECK 2: Mean difficulty per season ===")
    stats = df.groupby("season")["Opponent Difficulty"].agg(["min","max","mean","count"])
    print(stats)
    return stats


def check_team_profiles(df):
    print("\n=== CHECK 3: Team difficulty sanity profiles ===")

    easy_profile = (
        df[df["Opponent Name"].isin(EASY_TEAMS)]
        ["Opponent Difficulty"].mean()
    )
    hard_profile = (
        df[df["Opponent Name"].isin(HARD_TEAMS)]
        ["Opponent Difficulty"].mean()
    )

    print(f"Mean difficulty for EASY teams   : {easy_profile:.3f}")
    print(f"Mean difficulty for HARD teams   : {hard_profile:.3f}")

    if easy_profile < hard_profile:
        print("\nOK: Easy teams have LOWER difficulty than hard teams → Correct FPL direction.")
    else:
        print("\nWARNING: Easy teams have higher difficulty than hard teams → Scale may be inverted!")


def sample_difficulties(df):
    print("\n=== CHECK 4: Sample difficulties for known teams ===")

    teams_to_check = ["Man City", "Liverpool", "Arsenal", "Man Utd",
                      "Burnley", "Bournemouth", "Wolves", "Luton"]

    for team in teams_to_check:
        subset = df[df["Opponent Name"] == team]["Opponent Difficulty"]
        if len(subset) == 0:
            continue
        print(f"\n{team}: min={subset.min()}, max={subset.max()}, mean={subset.mean():.2f}")


def sample_fixture_rows(df):
    print("\n=== CHECK 5: Show random rows to manually confirm ===")
    print(df[["season","Gameweek","Opponent Name","Opponent Difficulty"]].sample(12))


def main():
    print("=" * 70)
    print("DEBUG OPPONENT DIFFICULTY SCALE")
    print("=" * 70)

    df = load_data()

    check_value_range(df)

    stats = check_means_per_season(df)

    check_team_profiles(df)

    sample_difficulties(df)

    sample_fixture_rows(df)

    print("\nFinished debugging difficulty scale.")
    print("=" * 70)


if __name__ == "__main__":
    main()

import pandas as pd

df = pd.read_csv("output/training_data.csv", encoding="utf-8-sig")

print(df.iloc[915:920][["season","Opponent Name","Opponent Difficulty"]])
