import pandas as pd
import requests
import os
from datetime import datetime
from controllers.player import Player
import math

BASE_DIR = "fpl_data"
PLAYER_DATA_FILE = os.path.join(BASE_DIR, "players_data.csv")
TEAMS_DATA_FILE = os.path.join(BASE_DIR, "teams_data.csv")
GW_HISTORY_DIR = os.path.join(BASE_DIR, "gameweek_history")
GW_FIXTURES_DIR = os.path.join(BASE_DIR, "gameweek_fixtures")
os.makedirs(GW_HISTORY_DIR, exist_ok=True)
os.makedirs(GW_FIXTURES_DIR, exist_ok=True)

os.makedirs(BASE_DIR, exist_ok=True)


def is_file_outdated(file_path):
    if not os.path.exists(file_path):
        return True
    last_modified_time = os.path.getmtime(file_path)
    return (datetime.now() - datetime.fromtimestamp(last_modified_time)).days > 10


def save_to_csv(data, file):
    df_data = pd.DataFrame(data)
    df_data.to_csv(file, index=False)
    return df_data


def fetch_data(data_type):
    """
    Fetch data for 'players' or 'teams' and return the corresponding DataFrame.
    Always fetch and save both players and teams when data is outdated but only
    load the requested type from CSV.

    Parameters:
        data_type (str): 'players' or 'teams'

    Returns:
        pd.DataFrame: DataFrame containing the requested data
    """
    if data_type not in {"players", "teams"}:
        raise ValueError("Invalid data type. Use 'players' or 'teams'.")

    # Determine the relevant file and API key
    file_map = {
        "players": PLAYER_DATA_FILE,
        "teams": TEAMS_DATA_FILE,
    }

    # Check if either file is outdated
    if is_file_outdated(PLAYER_DATA_FILE) or is_file_outdated(TEAMS_DATA_FILE):
        print("Fetching data from API...")
        url = "https://fantasy.premierleague.com/api/bootstrap-static/"
        response = requests.get(url)
        data = response.json()

        # Save both players and teams data to respective CSVs
        players = save_to_csv(data["elements"], PLAYER_DATA_FILE)
        teams = save_to_csv(data["teams"], TEAMS_DATA_FILE)
        return players if data_type == 'players' else teams

    # Load the requested data type from CSV
    file_path = file_map[data_type]
    print(f"Loading {data_type} data from CSV...")
    return pd.read_csv(file_path)


def fetch_gameweek_data(player_id, data_type):
    """
    Fetch or read gameweek data (history or fixtures) for a given player.

    Parameters:
        player_id (int): The ID of the player.
        data_type (str): Either 'history' or 'fixtures'.

    Returns:
        pd.DataFrame: DataFrame containing the requested data (history or fixtures).
    """
    if data_type not in {"history", "fixtures"}:
        raise ValueError("Invalid data type. Use 'history' or 'fixtures'.")

    # Paths to the history and fixtures CSVs
    history_file = os.path.join(GW_HISTORY_DIR, f"player_{
                                player_id}_history.csv")
    fixtures_file = os.path.join(GW_FIXTURES_DIR, f"player_{
                                 player_id}_fixtures.csv")
    file_map = {
        "history": history_file,
        "fixtures": fixtures_file,
    }

    # Determine if we need to fetch data
    if is_file_outdated(history_file) or is_file_outdated(fixtures_file):
        print(f"Fetching data for player {player_id} from API...")
        url = f"https://fantasy.premierleague.com/api/element-summary/{
            player_id}/"
        response = requests.get(url)
        data = response.json()

        # Save history and fixtures to their respective CSVs
        history = data.get("history", [])
        fixtures = data.get("fixtures", [])

        if history:
            save_to_csv(history, history_file)
            print(f"Saved history for player {player_id} to {history_file}")
        else:
            print(f"No history data found for player {player_id}.")

        if fixtures:
            save_to_csv(fixtures, fixtures_file)
            print(f"Saved fixtures for player {player_id} to {fixtures_file}")
        else:
            print(f"No fixtures data found for player {player_id}.")
    else:
        print(f"Data for player {player_id} is up-to-date.")

    # Return the requested data
    requested_file = file_map[data_type]
    if os.path.exists(requested_file):
        return pd.read_csv(requested_file)
    else:
        print(f"No {data_type} data available for player {player_id}.")
        return pd.DataFrame()


players = fetch_data('players').to_dict(orient="records")
teams = fetch_data('teams').to_dict(orient="records")
# gw_history = fetch_gameweek_data(3, 'history').to_dict(orient="records")

# Constants
BUDGET = 100.0
TEAM_SIZE = 15
POSITION_LIMITS = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}

# 🧩 UTILITY FUNCTIONS
def normalize_fitness(player):
    """Normalize player fitness or assume fully fit if null."""
    chance_of_playing = player.fitness
    if chance_of_playing is None or pd.isna(chance_of_playing) or (isinstance(chance_of_playing, float) and math.isnan(chance_of_playing)):
        return 1.0
    return chance_of_playing / 100

def calculate_performance(player, gw_history, fixtures, teams):
    """Calculate performance metrics for a player."""
    played_gws = [gw for gw in gw_history if gw.get("minutes", 0) > 0]
    last_played_gw = max(gw["round"] for gw in played_gws) if played_gws else 1
    next_fixture = min(fixtures, key=lambda x: x["event"])
    
    total_score = 0
    previous_difficulty = 0
    upcoming_difficulty = 0

    for gw in played_gws:
        score = player.calculate_performance_score_per_gw(gw, teams)
        weight = 1 + (gw["round"] / last_played_gw)
        total_score += score
        previous_difficulty += player.fixture_difficulty(gw, teams) * weight
    
    for fixture in fixtures:
        if fixture["event"] is None or pd.isna(fixture["event"]) or (isinstance(fixture["event"], float) and math.isnan(fixture["event"])):
            continue
        
        weight = 1 + (1 / max((fixture["event"] - next_fixture["event"]), 1))

        upcoming_difficulty += player.fixture_difficulty(fixture, teams) * weight

    num_gws = len(played_gws)
    player_availability = normalize_fitness(player)
    total_fitness_score = total_score * player_availability
    average_performance_score = total_fitness_score / num_gws if num_gws > 0 else 0

    price = player.price
    price_factor = math.log(price + 1)
    aggregate_score = total_score / price_factor if price > 0 else 0

    total_difficulty = previous_difficulty - upcoming_difficulty
    combined_score = aggregate_score / (1 + abs(total_difficulty))

    
    gw_difficulty = player.fixture_difficulty(next_fixture, teams)
    gw_score = average_performance_score / (1 + gw_difficulty)

    return {
        "ID": player.id,
        "GW played": num_gws,
        "Player": player.name,
        "Price": player.price / 10,
        "Position": player.position_name,
        "Performance Score": aggregate_score,
        "Previous Fixtures": previous_difficulty,
        "Upcoming Fixtures": upcoming_difficulty,
        "Combined score": combined_score,
        "Fitness": player_availability,
        "Gw score": gw_score,
        "team": player.team
    }

def select_team(df):
    """Select the best team based on budget, positions, and scores."""
    team = []
    temp_team = []
    total_cost = 0
    position_counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}

    def find_least_effective_player(team):
        """
        Identify the least effective player based on a modified score calculation.
        Prioritizes removing high-cost players with lower scores.
        """
        if not team:
            raise ValueError(
                "Team is empty. Cannot find the least effective player.")
        
        for player in team:
            player["Combined score"] = player["Combined score"] / (player["Price"] ** 0.005)
        return min(team, key=lambda x: x["Combined score"])
    
    def check_player_team_limit(temp_team, player_team):
        team_count = 0
        for player in temp_team:
            if player["team"] == player_team:
                team_count += 1
        return team_count == 3 

    while len(team) < TEAM_SIZE:
        selected = False
        for _, row in df.iterrows():
            position = row["Position"]
            price = row["Price"]
            player_team = row["team"]

            if position_counts[position] < POSITION_LIMITS[position] and \
                (total_cost + price) <= BUDGET and \
                row["Player"] not in [p["Player"] for p in temp_team] and \
                not check_player_team_limit(temp_team, player_team):
                temp_team.append(row)
                team.append(row)
                total_cost += price
                position_counts[position] += 1
                selected = True

        if not selected:
            least_effective = find_least_effective_player(team)
            team = [player for player in team if player["Player"] != least_effective["Player"]]
            total_cost -= least_effective["Price"]
            position_counts[least_effective["Position"]] -= 1

    return pd.DataFrame(team).sort_values(by="Gw score", ascending=False)


def split_starters_and_bench(final_team_df):
    """Separate starters and bench players."""
    starters = []
    bench = []

    # Goalkeepers
    gkps = final_team_df[final_team_df["Position"] == "GKP"]
    if not gkps.empty:
        starters.append(gkps.iloc[0].to_dict()) 

    for pos, min_count in [("DEF", 3), ("MID", 3), ("FWD", 1)]:
        position_players = final_team_df[final_team_df["Position"] == pos]
        starters.extend(position_players.iloc[:min_count].to_dict(orient='records'))

    remaining_spots = 11 - len(starters)
    remaining_players = final_team_df[
        ~final_team_df["Player"].isin([p["Player"] for p in starters + bench])
    ].head(remaining_spots)
    starters.extend(remaining_players.to_dict(orient='records'))

    bench_players = final_team_df[
        ~final_team_df["Player"].isin([p["Player"] for p in starters])
    ]
    bench.extend(bench_players.to_dict(orient='records'))

    return pd.DataFrame(starters), pd.DataFrame(bench)
    # return starters, bench


# 🚀 MAIN LOGIC
if __name__ == "__main__":
    total_scores = []
    for player_data in players:
        player = Player(player_data)

        if normalize_fitness(player) == 0:
            continue

        gw_history = fetch_gameweek_data(player.id, 'history').to_dict(orient="records")
        fixtures = fetch_gameweek_data(player.id, 'fixtures').to_dict(orient="records")

        player_stats = calculate_performance(player, gw_history, fixtures, teams)
        total_scores.append(player_stats)

    df = pd.DataFrame(total_scores).sort_values(by="Combined score", ascending=False)
    print(df)

    # Build Team
    final_team_df = select_team(df)
    print(final_team_df)

    # Split Starters and Bench
    starters_df, bench_df = split_starters_and_bench(final_team_df)

    # Display Results
    print("Starters:")
    print(starters_df)
    print("\nBench:")
    print(bench_df)
    print(f"Total Cost: {final_team_df['Price'].sum():.2f}M")

# results = []
# total_scores = []


# for player_data in players:
#     player = Player(player_data)

#     chance_of_playing = player.fitness
#     # Assume fully fit if no data
#     if chance_of_playing is None or pd.isna(chance_of_playing) or (isinstance(chance_of_playing, float) and math.isnan(chance_of_playing)):
#         chance_of_playing = 1.0
#     else:
#         chance_of_playing = chance_of_playing / 100  # Normalize to 0-1 scale

#     # Skip if explicitly marked as 0
#     if chance_of_playing == 0:
#         continue
#     gw_history = fetch_gameweek_data(
#         player.id, 'history').to_dict(orient="records")
#     fixtures = fetch_gameweek_data(
#         player.id, 'fixtures').to_dict(orient="records")

#     played_gws = [gw for gw in gw_history if gw.get("minutes", 0) > 0]
#     total_score = 0
#     previous_difficulty = 0
#     upcoming_difficulty = 0
#     current_gw = max(gw["round"] for gw in played_gws) if played_gws else 1
#     def get_next_fixture(fixtures, current_gw):
#         """
#         Get the next fixture for the player after the current gameweek.
#         """
#         upcoming_fixtures = [f for f in fixtures if f["event"] > current_gw]
        
#         if not upcoming_fixtures:
#             return None  # No upcoming fixtures found
        
#         # Sort fixtures by round and return the next one
#         next_fixture = sorted(upcoming_fixtures, key=lambda x: x["event"])[0]
#         return next_fixture

#     for gw in played_gws:
#         score = player.calculate_performance_score_per_gw(gw, teams)

#         # Weight score based on gameweek recency
#         weight = 1 + (gw["round"] / current_gw)
#         weighted_score = score * weight
        
#         total_score += score * weight

#         difficulty = player.fixture_difficulty(gw, teams)
#         previous_difficulty += difficulty

#         results.append({
#             "Player": player.name,
#             "GW": gw["round"],
#             "Fixture": gw["fixture"],
#             "Points": gw["total_points"],
#             "Performance Score": score
#         })

#     for fixture in fixtures:
#         fixture_gw = fixture.get("event", current_gw + 1)

#         weight = 1 + (1 / max((fixture_gw - current_gw), 1))
#         difficulty = player.fixture_difficulty(fixture, teams) * weight

#         upcoming_difficulty += difficulty

#     num_gws = len(played_gws)
#     total_fitness_score = total_score * chance_of_playing
#     average_performance_score = total_fitness_score / num_gws if num_gws > 0 else 0

#     price = player_data["now_cost"]
#     price_factor = math.log(price + 1)
#     aggregate_score = total_score  / price_factor if price > 0 else 0

#     total_difficulty = previous_difficulty - upcoming_difficulty

#     # combined_score = aggregate_score * total_difficulty

#     combined_score = aggregate_score / (1 + abs(total_difficulty))

#     next_fixture = get_next_fixture(fixtures, current_gw)
#     gw_difficulty = player.fixture_difficulty(next_fixture, teams)
#     gw_score = average_performance_score / (1 + gw_difficulty)

#     total_scores.append({
#         "ID": player.id,
#         "GW played": num_gws,
#         "Player": player.name,
#         "Price": player.price / 10,
#         "Position": player.position_name,
#         "Performance Score": aggregate_score,
#         "Previous Fixtures": previous_difficulty,
#         "Upcoming Fixtures": upcoming_difficulty,
#         "Combined score": combined_score,
#         "Fitness": chance_of_playing,
#         "Gw score": gw_score
#     })

# df = pd.DataFrame(total_scores)
# df = df.sort_values(by="Combined score", ascending=False)

# print(df)

# budget = 100.0
# team_size = 15
# position_limits = {"GKP": 2, "DEF": 5, "MID": 5, "FWD": 3}


# team = []
# temp_team = []
# total_cost = 0
# position_counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}


# def find_least_effective_player(team):
#     """
#     Identify the least effective player based on a modified score calculation.
#     Prioritizes removing high-cost players with lower scores.
#     """

#     if not team:
#         raise ValueError(
#             "Team is empty. Cannot find the least effective player.")

#     for player in team:
#         player["Combined score"] = player["Combined score"] / \
#             (player["Price"] ** 0.005)

#     return min(team, key=lambda x: x["Combined score"])


# while len(team) < team_size:
#     selected = False
#     for _, row in df.iterrows():
#         position = row["Position"]
#         price = row["Price"]

#         # Check position and budget constraints
#         if position_counts[position] < position_limits[position] and (total_cost + price) <= budget and row["Player"] not in [p["Player"] for p in temp_team]:
#             temp_team.append(row)
#             team.append(row)
#             total_cost += price
#             position_counts[position] += 1
#             selected = True

#         if not selected:
#             least_effective = find_least_effective_player(team)
#             team = [player for player in team if player["Player"]
#                     != least_effective["Player"]]
#             total_cost -= least_effective["Price"]
#             position_counts[least_effective["Position"]] -= 1


# final_team_df = pd.DataFrame(team)
# print(final_team_df)

# final_team_df = final_team_df.sort_values(by="Gw score", ascending=False)

# starters = []
# bench = []

# # Add the best Goalkeeper to starters, rest go to the bench
# gkps = final_team_df[final_team_df["Position"] == "GKP"]
# if not gkps.empty:
#     starters.append(gkps.iloc[0])
#     bench.extend(gkps.iloc[1:].to_dict(orient='records'))

# # Add Defenders, Midfielders, Forwards
# for pos, min_count in [("DEF", 3), ("MID", 3), ("FWD", 1)]:
#     position_players = final_team_df[final_team_df["Position"] == pos]
#     starters.extend(position_players.iloc[:min_count].to_dict(orient='records'))
#     bench.extend(position_players.iloc[min_count:].to_dict(orient='records'))

# # Fill remaining spots based on the highest Combined score
# remaining_spots = 11 - len(starters)
# remaining_players = final_team_df[
#     ~final_team_df["Player"].isin([p["Player"] for p in starters + bench])
# ].head(remaining_spots)

# starters.extend(remaining_players.to_dict(orient='records'))

# # Add remaining players to the bench
# bench_players = final_team_df[
#     ~final_team_df["Player"].isin([p["Player"] for p in starters])
# ]
# bench.extend(bench_players.to_dict(orient='records'))

# print(starters)
# print(bench)

# # Convert back to DataFrames
# starters_df = pd.DataFrame(starters)
# bench_df = pd.DataFrame(bench)

# print("Starters:")
# print(starters_df)
# print("\nBench:")
# print(bench_df)

# # Summary
# print(f"Total Cost: {total_cost:.2f}M")
# print(f"Position Counts: {position_counts}")
