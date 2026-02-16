import os
from pathlib import Path
import uuid
import re

import numpy as np
import pandas as pd
from unidecode import unidecode


# ============================================================
# CONFIG
# ============================================================
DATA_ROOT = Path("data") / "2025-26"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAINING_2025_PATH = OUTPUT_DIR / "training_data_2025_26.csv"

UUID_MAPPING_PATH = OUTPUT_DIR / "player_uuid_mapping.csv"
CLEANED_UUID_MAPPING_PATH = OUTPUT_DIR / "player_uuid_mapping_cleaned.csv"


# ============================================================
# Helper: normalize player name (ίδιο με FPLpipeline_v2)
# ============================================================
def normalize_player_name(name: str) -> str:
    if pd.isna(name):
        return name

    name = str(name).strip().lower()
    name = unidecode(name)

    # remove trailing numeric suffixes
    name = re.sub(r"[\s_]*\d+\s*$", "", name)

    # underscores → spaces
    name = name.replace("_", " ")

    # keep only alnum + space
    name = "".join(c for c in name if c.isalnum() or c.isspace())

    # collapse multiple spaces
    name = " ".join(name.split())
    return name


# ============================================================
# 1. Load 2025-26 GW data (from data/2025-26/gws/*.csv)
# ============================================================
print("📂 DATA_ROOT:", DATA_ROOT.resolve())

gws_path = DATA_ROOT / "gws"
if not gws_path.exists():
    raise SystemExit(f"❌ Folder not found: {gws_path}")

gw_files = sorted(
    [f for f in os.listdir(gws_path) if f.startswith("gw") and f.endswith(".csv")],
    key=lambda x: int(x.replace("gw", "").replace(".csv", ""))
)

if not gw_files:
    raise SystemExit(f"❌ No gw*.csv files in {gws_path}")

frames = []
for fname in gw_files:
    gw = int(fname.replace("gw", "").replace(".csv", ""))
    df = pd.read_csv(gws_path / fname)

    # unify column names with main pipeline
    if "Gameweek" not in df.columns:
        df["Gameweek"] = gw
    if "season" not in df.columns:
        df["season"] = "2025-26"

    keep = [
        "name", "element", "minutes", "goals_scored", "assists", "clean_sheets",
        "goals_conceded", "yellow_cards", "red_cards", "total_points",
        "influence", "creativity", "threat", "ict_index",
        "opponent_team", "was_home", "Gameweek", "season"
    ]
    cols = [c for c in keep if c in df.columns]
    df = df[cols].copy()

    frames.append(df)

df_gw = pd.concat(frames, ignore_index=True)
print(f"✅ GW rows (2025-26): {len(df_gw):,}")
print(df_gw.head())

# Ensure numeric types
df_gw["element"] = pd.to_numeric(df_gw["element"], errors="coerce").astype("Int64")
df_gw["Gameweek"] = pd.to_numeric(df_gw["Gameweek"], errors="coerce").astype("Int64")
df_gw["opponent_team"] = pd.to_numeric(df_gw["opponent_team"], errors="coerce").astype("Int64")


# ============================================================
# 2. Load players_raw (names, element_type)
# ============================================================
players_path = DATA_ROOT / "players_raw.csv"
if not players_path.exists():
    raise SystemExit(f"❌ Missing players_raw.csv at {players_path}")

players_raw = pd.read_csv(players_path)

# older dumps may use 'id' instead of 'element'
if "element" not in players_raw.columns and "id" in players_raw.columns:
    players_raw.rename(columns={"id": "element"}, inplace=True)

keep_pr = ["element", "team", "element_type", "web_name", "first_name", "second_name"]
keep_pr = [c for c in keep_pr if c in players_raw.columns]
players_raw = players_raw[keep_pr].copy()

players_raw["element"] = pd.to_numeric(players_raw["element"], errors="coerce").astype("Int64")
if "team" in players_raw.columns:
    players_raw["team"] = pd.to_numeric(players_raw["team"], errors="coerce").astype("Int64")

players_raw = players_raw.set_index("element")

print("✅ players_raw loaded:", len(players_raw))

# merge player info into GW data
df = df_gw.merge(
    players_raw[["element_type", "web_name", "first_name", "second_name"]],
    left_on="element", right_index=True, how="left"
)


# ============================================================
# 3. Load teams & fixtures and build Opponent Difficulty
#    ίδιο pattern με FPLpipeline_v2
# ============================================================
teams_path = DATA_ROOT / "teams.csv"
if not teams_path.exists():
    raise SystemExit(f"❌ Missing teams.csv at {teams_path}")
teams_df = pd.read_csv(teams_path)

idcol = "id" if "id" in teams_df.columns else "code"
teams_df.rename(columns={idcol: "Team ID", "name": "Team Name"}, inplace=True)
teams_df["Team ID"] = pd.to_numeric(teams_df["Team ID"], errors="coerce").astype("Int64")
if "short_name" not in teams_df.columns:
    teams_df["short_name"] = teams_df["Team Name"]

print("✅ teams.csv loaded:", len(teams_df))

fixtures_path = DATA_ROOT / "fixtures.csv"
if not fixtures_path.exists():
    raise SystemExit(f"❌ Missing fixtures.csv at {fixtures_path}")
fx = pd.read_csv(fixtures_path)

if "event" in fx.columns:
    fx["Gameweek"] = fx["event"]
elif "round" in fx.columns:
    fx["Gameweek"] = fx["round"]
else:
    raise SystemExit("❌ fixtures.csv has no 'event' or 'round' column")

fx["Gameweek"] = pd.to_numeric(fx["Gameweek"], errors="coerce").astype("Int64")
fx["team_h"] = pd.to_numeric(fx["team_h"], errors="coerce").astype("Int64")
fx["team_a"] = pd.to_numeric(fx["team_a"], errors="coerce").astype("Int64")
fx["team_h_difficulty"] = pd.to_numeric(fx["team_h_difficulty"], errors="coerce")
fx["team_a_difficulty"] = pd.to_numeric(fx["team_a_difficulty"], errors="coerce")

print("✅ fixtures.csv loaded:", len(fx))

# Build mapping (Gameweek, OppKey) → Player Team / Opponent / Is Home / Opponent Difficulty
rows = []
for _, r in fx.iterrows():
    gw = int(r["Gameweek"])
    h = int(r["team_h"])
    a = int(r["team_a"])
    dh = int(r["team_h_difficulty"])
    da = int(r["team_a_difficulty"])

    # όταν opponent_team == away team (a), ο παίκτης είναι στην home ομάδα (h)
    rows.append({
        "Gameweek": gw,
        "OppKey": a,
        "Player Team ID": h,
        "Opponent ID": a,
        "Is Home": True,
        "Opponent Difficulty": dh,
    })
    # όταν opponent_team == home team (h), ο παίκτης είναι στην away ομάδα (a)
    rows.append({
        "Gameweek": gw,
        "OppKey": h,
        "Player Team ID": a,
        "Opponent ID": h,
        "Is Home": False,
        "Opponent Difficulty": da,
    })

fixture_map = pd.DataFrame(rows)
fixture_map["Gameweek"] = pd.to_numeric(fixture_map["Gameweek"], errors="coerce").astype("Int64")
fixture_map["OppKey"] = pd.to_numeric(fixture_map["OppKey"], errors="coerce").astype("Int64")
fixture_map["Player Team ID"] = pd.to_numeric(fixture_map["Player Team ID"], errors="coerce").astype("Int64")
fixture_map["Opponent ID"] = pd.to_numeric(fixture_map["Opponent ID"], errors="coerce").astype("Int64")

print("✅ fixture_map rows:", len(fixture_map))

# merge with GW data
df = df.merge(
    fixture_map,
    left_on=["Gameweek", "opponent_team"],
    right_on=["Gameweek", "OppKey"],
    how="left"
).drop(columns=["OppKey"])

# Map team names
team_name_map = dict(zip(teams_df["Team ID"], teams_df["Team Name"]))
df["Player Team Name"] = df["Player Team ID"].map(team_name_map)
df["Opponent Name"] = df["Opponent ID"].map(team_name_map)

print("🔍 Sample with Opponent Difficulty:")
print(df[[
    "name", "season", "Gameweek",
    "Player Team ID", "Player Team Name",
    "Opponent ID", "Opponent Name",
    "Is Home", "Opponent Difficulty"
]].head())


# ============================================================
# 4. Canonical columns, injury flag, rolling averages
# ============================================================
POS_MAP = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

rename_map = {
    "element": "Code",
    "minutes": "Minutes Played",
    "goals_scored": "Goals Scored",
    "assists": "Assists",
    "clean_sheets": "Clean Sheet",
    "goals_conceded": "Goals Conceded",
    "yellow_cards": "Yellow Card",
    "red_cards": "Red Cards",
    "total_points": "Total Points",
    "influence": "Influence",
    "creativity": "Creativity",
    "threat": "Threat",
    "ict_index": "ICT Index",
}

df_clean = df.copy()
df_clean.rename(columns=rename_map, inplace=True)

# Position from element_type
if "element_type" in df_clean.columns:
    df_clean["Position"] = df_clean["element_type"].map(POS_MAP)
else:
    df_clean["Position"] = np.nan

# Player Name & Web Name
df_clean["Player Name"] = (
    df_clean["first_name"].fillna("").astype(str) + " " +
    df_clean["second_name"].fillna("").astype(str)
).str.strip()
df_clean["Player Name"] = df_clean["Player Name"].where(df_clean["Player Name"] != "", df_clean["name"])
df_clean["Web Name"] = df_clean["web_name"]

# Normalized name
df_clean["Player Name Norm"] = df_clean["Player Name"].apply(normalize_player_name)

print("✅ Basic cleaning done.")
print(df_clean[[
    "Player Name", "Player Name Norm", "Player Team Name",
    "Opponent Name", "Total Points"
]].head())

# Injury flag (3+ consecutive games with 0 minutes)
df_clean = df_clean.sort_values(["Player Name Norm", "season", "Gameweek"])
df_clean["Injury/Unavailable"] = 0

for pname in df_clean["Player Name Norm"].unique():
    mask = df_clean["Player Name Norm"] == pname
    m = df_clean.loc[mask, "Minutes Played"]
    streak = 0
    flags = []
    for x in m:
        if x == 0:
            streak += 1
            flags.append(1 if streak >= 3 else 0)
        else:
            streak = 0
            flags.append(0)
    df_clean.loc[mask, "Injury/Unavailable"] = flags

print("✅ Injury/Unavailable flag created.")


def add_lagged(df_in: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "Total Points", "Minutes Played", "Goals Scored", "Assists",
        "Goals Conceded", "ICT Index", "Threat", "Creativity", "Influence",
    ]

    df_in = df_in.sort_values(["Player Name Norm", "season", "Gameweek"])

    for w in (3, 5):
        for c in metrics:
            if c not in df_in.columns:
                continue
            new_col = f"Avg_{c}_L{w}"
            df_in[new_col] = (
                df_in.groupby(["Player Name Norm", "season"])[c]
                .transform(lambda s: s.shift(1).rolling(w, min_periods=1).mean())
                .fillna(0)
            )
    return df_in


df_lagged = add_lagged(df_clean)
print("✅ Rolling L3/L5 features added.")


# ============================================================
# 5. Attach Player UUIDs (read-only mapping)
# ============================================================
uuid_map = {}

mapping_path = None
if CLEANED_UUID_MAPPING_PATH.exists():
    mapping_path = CLEANED_UUID_MAPPING_PATH
elif UUID_MAPPING_PATH.exists():
    mapping_path = UUID_MAPPING_PATH

if mapping_path is not None:
    print(f"📥 Using existing UUID mapping from: {mapping_path}")
    mapping_df = pd.read_csv(mapping_path)
    # find cols ignoring case
    cols_lower = {c.lower(): c for c in mapping_df.columns}
    name_col = cols_lower.get("player name norm")
    uid_col = cols_lower.get("player uuid")
    if name_col and uid_col:
        uuid_map = dict(zip(mapping_df[name_col].astype(str), mapping_df[uid_col].astype(str)))
    else:
        print("⚠️ UUID mapping file does not have expected columns. Will create new UUIDs for all players.")
else:
    print("⚠️ No UUID mapping file found. Will create new UUIDs for all players.")

uuids = []
for norm_name in df_lagged["Player Name Norm"]:
    key = str(norm_name)
    if key in uuid_map:
        uuids.append(uuid_map[key])
    else:
        uuids.append(str(uuid.uuid4()))
df_lagged["Player UUID"] = uuids

print("✅ Player UUIDs attached (read-only mapping, no files modified).")


# ============================================================
# 6. Team Contribution Features (no leakage, simple version)
# ============================================================
print("\n📊 Adding Team Contribution features (2025-26 only)...")

df_tc = df_lagged.copy()

# force numeric
for col in [
    "Total Points", "Minutes Played", "Goals Scored", "Assists",
    "Clean Sheet", "Goals Conceded", "Yellow Card", "Red Cards",
    "Threat", "ICT Index", "Influence", "Creativity",
]:
    if col in df_tc.columns:
        df_tc[col] = pd.to_numeric(df_tc[col], errors="coerce").fillna(0)

player_id_col = "Player UUID"

# Team total points per GW
team_points = (
    df_tc.groupby(["Player Team Name", "season", "Gameweek"])["Total Points"]
    .sum()
    .reset_index()
    .rename(columns={"Total Points": "Team_Total_Points_GW"})
)

team_points["Team_Total_Points_GW"] = pd.to_numeric(
    team_points["Team_Total_Points_GW"], errors="coerce"
).fillna(0)

team_points["Team_Total_Points_CUM"] = (
    team_points.groupby(["Player Team Name", "season"])["Team_Total_Points_GW"].cumsum()
)

team_points["Team_Total_Points_Causal"] = (
    team_points.groupby(["Player Team Name", "season"])["Team_Total_Points_CUM"].shift(1)
)

df_tc = df_tc.merge(
    team_points[
        ["Player Team Name", "season", "Gameweek",
         "Team_Total_Points_GW", "Team_Total_Points_CUM", "Team_Total_Points_Causal"]
    ],
    on=["Player Team Name", "season", "Gameweek"],
    how="left",
)

df_tc["Team_Total_Points_GW"] = df_tc["Team_Total_Points_GW"].fillna(0)
df_tc["Team_Total_Points"] = df_tc["Team_Total_Points_Causal"].fillna(0)

# Player cumulative season points (causal)
df_tc["Player_Season_Points"] = (
    df_tc.groupby([player_id_col, "season"])["Total Points"]
    .cumsum()
    .shift(1)
    .fillna(0)
)

# Contribution metrics
df_tc["Team_Points_Contribution_GW"] = np.where(
    df_tc["Team_Total_Points_GW"] > 0,
    df_tc["Total Points"] / df_tc["Team_Total_Points_GW"],
    0,
).round(5)

df_tc["Team_Points_Contribution_Causal"] = np.where(
    df_tc["Team_Total_Points"] > 0,
    df_tc["Player_Season_Points"] / df_tc["Team_Total_Points"],
    0,
).round(5)

# Ranks within team per GW
df_tc["Team_Contribution_Rank_GW"] = (
    df_tc.groupby(["Player Team Name", "season", "Gameweek"])["Team_Points_Contribution_GW"]
    .rank(method="min", ascending=False, pct=True)
).round(4)

df_tc["Team_Contribution_Rank_Causal"] = (
    df_tc.groupby(["Player Team Name", "season", "Gameweek"])["Team_Points_Contribution_Causal"]
    .rank(method="min", ascending=False, pct=True)
).round(4)

# convenient percentage versions
for col in ["Team_Points_Contribution_GW", "Team_Points_Contribution_Causal"]:
    df_tc[col + "_Pct"] = (df_tc[col] * 100).round(2)

print("✅ Team Contribution features added.")


# ============================================================
# 7. Final save (training_data_2025_26.csv)
# ============================================================
base_cols = [
    "Player UUID", "Code", "Player Name", "Web Name", "Player Team Name",
    "season", "Gameweek", "Minutes Played", "Goals Scored", "Assists",
    "Clean Sheet", "Goals Conceded", "Yellow Card", "Red Cards",
    "Total Points", "Threat", "ICT Index", "Influence", "Creativity",
    "Opponent Name", "Opponent Difficulty", "Is Home", "Position",
    "Injury/Unavailable",
]

lagged_cols = [c for c in df_tc.columns if c.startswith("Avg_")]

tc_cols = [
    "Team_Total_Points_GW", "Team_Total_Points", "Player_Season_Points",
    "Team_Points_Contribution_GW", "Team_Points_Contribution_Causal",
    "Team_Contribution_Rank_GW", "Team_Contribution_Rank_Causal",
    "Team_Points_Contribution_GW_Pct", "Team_Points_Contribution_Causal_Pct",
]

final_cols = base_cols + lagged_cols + tc_cols
final_cols = [c for c in final_cols if c in df_tc.columns]

df_final = df_tc[final_cols].copy()

df_final.to_csv(TRAINING_2025_PATH, index=False, encoding="utf-8-sig")

print("\n🎉 training_data_2025_26.csv CREATED!")
print("   Path:", TRAINING_2025_PATH)
print("   Rows:", len(df_final))
print("   Cols:", len(df_final.columns))
print(df_final.head())


