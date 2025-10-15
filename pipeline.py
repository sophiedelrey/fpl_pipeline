import os
import pandas as pd
import numpy as np
from unidecode import unidecode  # Needed for name normalization

DATA_ROOT = "data"
OUTPUT_FILE = "output/training_data.csv"


# Helper Functions : Load Data
def load_all_gameweeks(data_root=DATA_ROOT):
    """Load and concatenate all gameweek CSVs."""
    all_data = []
    print("\nLoading Gameweek Data...")
    for season in sorted(os.listdir(data_root)):
        season_path = os.path.join(data_root, season)
        if not os.path.isdir(season_path):
            continue
        gws_path = os.path.join(season_path, "gws")
        search_path = gws_path if os.path.exists(gws_path) else season_path
        gw_files = sorted(
            [f for f in os.listdir(search_path) if f.startswith("gw") and f.endswith(".csv")],
            key=lambda x: int(x.replace("gw", "").replace(".csv", ""))
        )
        if not gw_files:
            continue
        print(f" • Season: {season} ({len(gw_files)} gameweeks)")
        for filename in gw_files:
            gw_number = int(filename.replace("gw", "").replace(".csv", ""))
            gw_path = os.path.join(search_path, filename)
            try:
                df = pd.read_csv(gw_path, encoding="utf-8")
                df["season"] = season
                df["Gameweek"] = gw_number
                all_data.append(df)
            except Exception as e:
                print(f" ERROR reading {filename}: {e}")
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        print(" → No gameweek data found.")
        return pd.DataFrame()


def load_fixtures(data_root=DATA_ROOT):
    """Load and concatenate all fixtures CSVs."""
    all_fx = []
    print("\nLoading Fixtures Data...")
    for season in sorted(os.listdir(data_root)):
        season_path = os.path.join(data_root, season)
        if not os.path.isdir(season_path):
            continue
        fixtures_file = os.path.join(season_path, "fixtures.csv")
        if not os.path.exists(fixtures_file):
            continue
        try:
            fx = pd.read_csv(fixtures_file, encoding="utf-8")
            fx["season"] = season
            all_fx.append(fx)
        except Exception as e:
            print(f" ERROR loading fixtures for {season}: {e}")
    if all_fx:
        print(f" → Loaded fixtures for {len(all_fx)} seasons.")
        return pd.concat(all_fx, ignore_index=True)
    else:
        print(" → No fixtures data found.")
        return pd.DataFrame()


def load_teams(data_root=DATA_ROOT):
    """Load and map team names to IDs."""
    teams_by_season = {}
    print("\nLoading Teams Data...")
    for season in sorted(os.listdir(data_root)):
        season_path = os.path.join(data_root, season)
        if not os.path.isdir(season_path):
            continue
        teams_file = os.path.join(season_path, "teams.csv")
        if os.path.exists(teams_file):
            try:
                teams_df = pd.read_csv(teams_file, encoding="utf-8")
                teams_df["id"] = pd.to_numeric(teams_df["id"], errors="coerce").astype("Int64")
                teams_by_season[season] = dict(zip(teams_df["name"], teams_df["id"]))
            except Exception as e:
                print(f" ERROR loading teams for {season}: {e}")
    if teams_by_season:
        print(f" → Loaded teams for {len(teams_by_season)} seasons.")
    return teams_by_season


# Player name normalization
def normalize_player_name(name):
    if pd.isnull(name):
        return name
    name = str(name).strip().lower()
    name = unidecode(name)
    name = name.replace("_", " ")
    name = "".join(c for c in name if c.isalnum() or c.isspace())
    return name


# Feature Engineering----
def add_lagged_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates rolling mean features over the last 3 and 5 Gameweeks (excluding the current GW).
    The shift(1) is used to align the average of GWs (N-5 to N-1) with GW N.
    """
    print("\nAdding Lagged Features (Rolling Averages)...")

    df = df.sort_values(["Player Name Norm", "season", "Gameweek"]).reset_index(drop=True)

    rolling_metrics = [
        "Total Points", "Minutes Played", "Goals Scored", "Assists",
        "Goals Conceded", "ICT Index", "Threat", "Creativity", "Influence"
    ]

    for window in [3, 5]:
        for col in rolling_metrics:
            new_col_name = f"Avg_{col}_L{window}"
            df[new_col_name] = df.groupby(["Player Name Norm", "season"])[col] \
                .transform(lambda x: x.shift(1).rolling(window=window, min_periods=1).mean())
            df[new_col_name] = df[new_col_name].fillna(0)

    print(f" → Added {len(rolling_metrics) * 2} lagged features.")
    return df


def clean_dataset(df: pd.DataFrame, fixtures: pd.DataFrame, teams_by_season: dict) -> pd.DataFrame:
    """Cleans, renames, and enriches the gameweek data."""
    print("\nCleaning and Enriching Dataset...")

    keep_cols = [
        "element", "name", "team", "opponent_team", "was_home", "season", "Gameweek",
        "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded",
        "yellow_cards", "red_cards", "bonus", "total_points",
        "influence", "creativity", "threat", "ict_index", "position"
    ]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    col_map = {
        "element": "Code", "name": "Player Name", "team": "Player Team Name",
        "opponent_team": "Opponent ID", "was_home": "Is Home", "minutes": "Minutes Played",
        "goals_scored": "Goals Scored", "assists": "Assists", "clean_sheets": "Clean Sheet",
        "goals_conceded": "Goals Conceded", "yellow_cards": "Yellow Card", "red_cards": "Red Cards",
        "bonus": "Bonus Points", "total_points": "Total Points", "influence": "Influence",
        "creativity": "Creativity", "threat": "Threat", "ict_index": "ICT Index",
        "position": "Position"
    }
    df.rename(columns=col_map, inplace=True)

    df["Player Name Norm"] = df["Player Name"].apply(normalize_player_name)

    df["Player Team ID"] = df.apply(
        lambda r: teams_by_season.get(r["season"], {}).get(r["Player Team Name"]), axis=1
    )

    def get_team_name(row):
        season_teams = teams_by_season.get(row["season"], {})
        id_to_name = {v: k for k, v in season_teams.items()}
        if pd.notna(row["Opponent ID"]):
            try:
                return id_to_name.get(int(row["Opponent ID"]))
            except:
                return pd.NA
        return pd.NA

    df["Opponent Name"] = df.apply(get_team_name, axis=1)

    df["Gameweek"] = pd.to_numeric(df["Gameweek"], errors="coerce").astype(pd.Int64Dtype())
    df["Player Team ID"] = pd.to_numeric(df["Player Team ID"], errors="coerce").astype(pd.Int64Dtype())
    df["Opponent ID"] = pd.to_numeric(df["Opponent ID"], errors="coerce").astype(pd.Int64Dtype())
    df["Is Home"] = df["Is Home"].astype(bool)

    df["Opponent Difficulty"] = np.nan
    if not fixtures.empty:
        fx = fixtures.copy()
        fx.rename(columns={
            "event": "Gameweek", "team_h": "team_h_id", "team_a": "team_a_id",
            "team_h_difficulty": "Home Difficulty", "team_a_difficulty": "Away Difficulty"
        }, inplace=True)
        fx["team_h_id"] = pd.to_numeric(fx["team_h_id"], errors="coerce").astype(pd.Int64Dtype())
        fx["team_a_id"] = pd.to_numeric(fx["team_a_id"], errors="coerce").astype(pd.Int64Dtype())
        fx["Gameweek"] = pd.to_numeric(fx["Gameweek"], errors="coerce").astype(pd.Int64Dtype())
        merge_cols = ["season", "Gameweek", "team_h_id", "team_a_id", "Home Difficulty", "Away Difficulty"]
        fx_subset = fx[merge_cols].drop_duplicates()

        home_games = df[df["Is Home"] == True].copy()
        merged_home = home_games.merge(
            fx_subset[["season", "Gameweek", "team_h_id", "team_a_id", "Home Difficulty"]],
            left_on=["season", "Gameweek", "Player Team ID", "Opponent ID"],
            right_on=["season", "Gameweek", "team_h_id", "team_a_id"],
            how="left"
        )
        df.loc[df["Is Home"] == True, "Opponent Difficulty"] = merged_home["Home Difficulty"].values

        away_games = df[df["Is Home"] == False].copy()
        merged_away = away_games.merge(
            fx_subset[["season", "Gameweek", "team_h_id", "team_a_id", "Away Difficulty"]],
            left_on=["season", "Gameweek", "Player Team ID", "Opponent ID"],
            right_on=["season", "Gameweek", "team_a_id", "team_h_id"],
            how="left"
        )
        df.loc[df["Is Home"] == False, "Opponent Difficulty"] = merged_away["Away Difficulty"].values

        print(f" → Opponent Difficulty filled: {df['Opponent Difficulty'].notna().sum()}/{len(df)} rows")
    else:
        print(" WARNING: No fixtures loaded, Opponent Difficulty remains empty.")

    df = df.sort_values(["Player Name Norm", "season", "Gameweek"]).reset_index(drop=True)
    df["Injury/Unavailable"] = 0

    for player_norm in df["Player Name Norm"].unique():
        mask = df["Player Name Norm"] == player_norm
        player_data = df.loc[mask].copy()

        consecutive_zeros = 0
        injury_flags = []

        for minutes in player_data["Minutes Played"]:
            if minutes == 0:
                consecutive_zeros += 1
                if consecutive_zeros >= 3:
                    injury_flags.append(1)
                else:
                    injury_flags.append(0)
            else:
                consecutive_zeros = 0
                injury_flags.append(0)

        df.loc[mask, "Injury/Unavailable"] = injury_flags

    injured_count = df["Injury/Unavailable"].sum()
    print(f" → Injury/Unavailable indicator added: {injured_count} records marked (3+ consecutive GWs with 0 minutes)")

    key_cols = ["season", "Player Name Norm", "Gameweek", "Position", "Player Team Name"]
    agg_dict = {
        "Minutes Played": "sum",
        "Goals Scored": "sum",
        "Assists": "sum",
        "Clean Sheet": "sum",
        "Goals Conceded": "sum",
        "Yellow Card": "sum",
        "Red Cards": "sum",
        "Bonus Points": "sum",
        "Total Points": "sum",
        "ICT Index": "mean",
        "Influence": "mean",
        "Creativity": "mean",
        "Threat": "mean",
        "Opponent Difficulty": "mean",
        "Injury/Unavailable": "max",
        "Player Name": "first",
        "Player Team Name": "first",
        "Opponent Name": "first",
        "Is Home": "first",
        "Code": "first",
        "Position": "first"
    }
    before = len(df)
    df = df.groupby(key_cols, as_index=False).agg(agg_dict)
    after = len(df)
    print(f"Duplicates merged: {before - after} rows combined (Player + Gameweek + Position + Team)")

    df["Web Name"] = df["Player Name"].apply(lambda x: str(x).split()[0] if pd.notna(x) else x)

    return df


def main():
    """Main function to run the data pipeline."""
    print("\n>>> Fantasy Premier League Data Pipeline Started <<<")
    df = load_all_gameweeks()
    if df.empty:
        print("\nERROR: No gameweek data found!")
        return
    fixtures = load_fixtures()
    teams_by_season = load_teams()

    df_clean = clean_dataset(df, fixtures, teams_by_season)
    df_lagged = add_lagged_features(df_clean)

    final_cols = [
        "Code", "Player Name", "Web Name", "Player Team Name", "season", "Gameweek",
        "Minutes Played", "Goals Scored", "Assists", "Clean Sheet", "Goals Conceded",
        "Yellow Card", "Red Cards", "Bonus Points", "Total Points", "Threat",
        "ICT Index", "Influence", "Creativity", "Opponent Name", "Opponent Difficulty",
        "Is Home", "Position", "Injury/Unavailable"
    ]

    lagged_cols = [col for col in df_lagged.columns if col.startswith("Avg_")]
    final_cols.extend(lagged_cols)

    df_final = df_lagged.reindex(columns=final_cols, fill_value=np.nan)
    df_final = df_final.sort_values(by=["Player Name", "season", "Gameweek"], ignore_index=True)
    df_final.insert(0, "A", df_final.index)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df_final.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 50)
    print(f"Pipeline Done. Output saved to: {OUTPUT_FILE}")
    print(f" Total rows: {len(df_final)}")
    print(f" Total features (columns): {len(df_final.columns) - 1}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
