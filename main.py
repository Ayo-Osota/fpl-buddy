import pandas as pd
import requests
import os
from datetime import datetime

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
    return (datetime.now() - datetime.fromtimestamp(last_modified_time)).days > 0


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
gw_history = fetch_gameweek_data(3, 'history').to_dict(orient="records")

print(gw_history)
print(players)
# for element in data:
#     print(element)

# def calculate_player_score(player, holding_gws, fixtures_df, teams_df):
#     """
#     Calculate the score for a single player.
#     """
#     # Extract factors
#     ppg = player['points_per_game']  # Player stats
#     fitness = player['minutes'] / (90 * holding_gws)  # Fitness (scaled by holding period)
#     team_form = teams_df.loc[player['team'], 'recent_form']  # Team performance
#     fixture_difficulty = fixtures_df.loc[player['team'], :holding_gws].mean()  # Avg fixture difficulty

#     # Opponent strength
#     upcoming_fixtures = fixtures_df.loc[player['team'], :holding_gws]
#     avg_opponent_strength = upcoming_fixtures.mean()

#     # Weights
#     weights = {
#         'stats': 0.3,
#         'fitness': 0.2,
#         'opponent_strength': 0.2,
#         'fixtures': 0.2,
#         'team_form': 0.1,
#     }

#     # Calculate final score
#     score = (
#         weights['stats'] * ppg +
#         weights['fitness'] * fitness +
#         weights['opponent_strength'] * (1 / avg_opponent_strength) +  # Inverse for weaker opponents
#         weights['fixtures'] * (1 / fixture_difficulty) +  # Favor easier fixtures
#         weights['team_form'] * team_form
#     )
#     return score

# def find_best_players(players_df, fixtures_df, teams_df, holding_gws=3, top_n=10):
#     """
#     Find the best players based on the scoring algorithm.
#     """
#     players_df['score'] = players_df.apply(
#         lambda player: calculate_player_score(player, holding_gws, fixtures_df, teams_df),
#         axis=1
#     )
#     return players_df.sort_values(by='score', ascending=False).head(top_n)

# # Example DataFrames
# players_data = {
#     'id': [1, 2, 3],
#     'name': ['Player A', 'Player B', 'Player C'],
#     'team': ['Team X', 'Team Y', 'Team Z'],
#     'points_per_game': [5.2, 4.8, 6.0],
#     'minutes': [270, 250, 300],  # Last 3 GWs
# }

# fixtures_data = {
#     'Team X': [2, 3, 4],  # Fixture difficulty for upcoming GWs
#     'Team Y': [5, 4, 3],
#     'Team Z': [1, 2, 2],
# }

# teams_data = {
#     'Team X': {'recent_form': 0.7},
#     'Team Y': {'recent_form': 0.6},
#     'Team Z': {'recent_form': 0.8},
# }

# # Convert to DataFrame
# players_df = pd.DataFrame(players_data)
# fixtures_df = pd.DataFrame(fixtures_data).T
# teams_df = pd.DataFrame(teams_data).T

# # Run the algorithm
# best_players = find_best_players(players_df, fixtures_df, teams_df, holding_gws=3, top_n=2)
# print(best_players)
