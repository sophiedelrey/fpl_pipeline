import pandas as pd
import numpy as np
from pathlib import Path

DATA_PATH = Path("output/training_data.csv")
BACKUP_PATH = Path("output/training_data_backup_before_OD_fix.csv")


def detect_inverted_seasons(df):
    """Return seasons that appear to use inverted difficulty scale."""
    season_stats = (
        df.groupby("season")["Opponent Difficulty"]
        .agg(["min", "max", "mean", "count"])
        .sort_index()
    )

    print("\nOpponent Difficulty Stats per Season:")
    print(season_stats)

    # Detect inverted scales: mean < 2.5
    mask_inverted = season_stats["mean"] < 2.5
    inverted_seasons = season_stats[mask_inverted].index.tolist()

    print(f"\nPotentially inverted seasons: {inverted_seasons}")

    return inverted_seasons, season_stats


def normalize_opponent_difficulty(df, inverted_seasons):
    """Apply inversion fix (6 - x) for selected seasons."""
    if not inverted_seasons:
        print("\nNo inverted seasons found — no normalization needed.")
        return df

    print("\nApplying normalization (6 - difficulty) to seasons:")
    for season in inverted_seasons:
        print(f"  - {season}")
        mask = df["season"] == season
        df.loc[mask, "Opponent Difficulty"] = (
            6 - df.loc[mask, "Opponent Difficulty"]
        )

    print("\nNormalization applied.")
    return df


def main():
    print("=" * 70)
    print("CORRECT OPPONENT DIFFICULTY SCALING")
    print("=" * 70)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"File not found: {DATA_PATH}")

    print(f"\nLoading {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    # Detect inverted seasons
    inverted_seasons, stats_before = detect_inverted_seasons(df)

    # Backup BEFORE changes
    print(f"\nCreating backup at: {BACKUP_PATH}")
    df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")
    print("Backup created.")

    # Normalize difficulty
    df = normalize_opponent_difficulty(df, inverted_seasons)

    # Stats AFTER fix
    inverted_after, stats_after = detect_inverted_seasons(df)

    print("\nStats AFTER normalization:")
    print(stats_after)

    if inverted_after:
        print("\nWarning: Some seasons still appear inverted.")
        print(inverted_after)
        print("Check these seasons manually.")
    else:
        print("\nAll seasons now use consistent FPL difficulty scale (1=easy → 5=hard).")

    # Save updated file
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    print(f"\nSaved corrected dataset to {DATA_PATH}")

    print("\nDone.")
    print("=" * 70)


if __name__ == "__main__":
    main()
