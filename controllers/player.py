from controllers.team import get_team, Team


class Player:
    def __init__(self, player_data):
        self.id = player_data.get("id")
        self.photo = player_data.get("photo")
        self.name = player_data.get("web_name")
        self.form = float(player_data.get("form", 0.0))
        self.position = player_data.get("element_type")

        match self.position:
            case 1:
                self.position_name = "GKP"
            case 2:
                self.position_name = "DEF"
            case 3:
                self.position_name = "MID"
            case 4:
                self.position_name = "FWD"

        self.fitness = float(player_data.get("chance_of_playing_next_round", 100.0))
        self.team = player_data.get("team")
        self.bonus = player_data.get("bonus")
        self.price = player_data.get("now_cost")

        self.points_per_game = float(player_data.get("points_per_game", 0.0))
        self.selected_by_percent = float(
            player_data.get("selected_by_percent", 0))
        self.minutes = float(player_data.get("minutes", 0))
        self.starts = float(player_data.get("starts", 0))
        self.penalties_order = player_data.get("penalties_order")
        self.total_points = int(player_data.get("total_points", 0))

        self.goals_scored = float(player_data.get("goals_scored", 0))
        self.assists = float(player_data.get("assists", 0))
        self.clean_sheets = float(player_data.get("clean_sheets", 0))
        self.penalties_saved = float(player_data.get("penalties_saved", 0))
        self.saves = float(player_data.get("saves", 0))

        self.goals_conceded = float(player_data.get("goals_conceded", 0))
        self.own_goals = float(player_data.get("own_goals", 0))
        self.penalties_missed = float(player_data.get("penalties_missed", 0))
        self.yellow_cards = float(player_data.get("yellow_cards", 0))

        self.influence = float(player_data.get("influence", 0.0))
        self.creativity = float(player_data.get("creativity", 0.0))
        self.threat = float(player_data.get("threat", 0.0))
        self.ict_index = float(player_data.get("ict_index", 0.0))
        self.xG = float(player_data.get("expected_goals", 0.0))
        self.xA = float(player_data.get("expected_assists", 0.0))
        self.expected_goal_involvements = float(
            player_data.get("expected_goal_involvements", 0.0))
        self.expected_goals_conceded = float(
            player_data.get("expected_goals_conceded", 0.0))
        self.influence_rank = int(player_data.get("influence_rank", 0))
        self.threat_rank = int(player_data.get("threat_rank", 0))
        self.creativity_rank = int(player_data.get("creativity_rank", 0))
        self.ict_index_rank = int(player_data.get("ict_index_rank", 0))
        self.expected_goals_per_90 = float(
            player_data.get("expected_goals_per_90", 0))
        self.expected_assists_per_90 = float(
            player_data.get("expected_assists_per_90", 0))
        self.saves_per_90 = float(player_data.get("saves_per_90", 0))
        self.starts_per_90 = float(player_data.get("starts_per_90", 0))
        self.clean_sheets_per_90 = float(
            player_data.get("clean_sheets_per_90", 0))
        self.corners_and_indirect_freekicks_order = player_data.get(
            "corners_and_indirect_freekicks_order")
        self.direct_freekicks_order = player_data.get("direct_freekicks_order")

        # self.fixture = player_data.get("fixture")
        # self.opponent_team = player_data.get("opponent_team")
        # self.was_home = player_data.get("was_home")
        # self.minutes = player_data.get("minutes")
        # self.goals_scored = player_data.get("goals_scored")
        # self.assists = player_data.get("assists")
        # self.clean_sheets = player_data.get("clean_sheets")
        # self.goals_conceded = player_data.get("goals_conceded")
        # self.bonus = player_data.get("bonus")
        # self.influence = float(player_data.get("influence", 0))
        # self.creativity = float(player_data.get("creativity", 0))
        # self.threat = float(player_data.get("threat", 0))
        # self.ict_index = float(player_data.get("ict_index", 0))
        # self.expected_goals = float(player_data.get("expected_goals", 0))
        # self.expected_assists = float(player_data.get("expected_assists", 0))
        # self.expected_goal_involvements = float(player_data.get("expected_goal_involvements", 0))
        # self.expected_goals_conceded = float(player_data.get("expected_goals_conceded", 0))
        # self.value = player_data.get("value")

    def calculate_performance_score_per_gw(self, gw_data, teams):
        """
        Calculate a player performance score per gw based on various factors.  HOME STRIKER
        """

        xTotal = gw_data['expected_goals'] + gw_data['expected_assists'] + \
            gw_data['expected_goal_involvements']

        if self.position != 4:
            xTotal -= gw_data['expected_goals_conceded']

        total_score = (
            gw_data['ict_index'] + gw_data['total_points'] + xTotal)

        # Normalize the score
        normalized_score = max(0, round(total_score, 2))

        return normalized_score

    def fixture_difficulty(self, fixture, teams):
        team_data = Team(get_team(self.team, teams))
        opponent_team_id = fixture.get("opponent_team") or (fixture.get(
            "team_h") if self.team == fixture.get("team_a") else fixture.get("team_a"))

        if opponent_team_id:
            opponent_team = Team(get_team(opponent_team_id, teams))
        else:
            raise ValueError("No valid opponent team found in the fixture data")

        was_home = fixture.get("was_home")
        team_h = fixture.get("team_h")

        if was_home or team_h == self.team:
            player_strength_type = "strength_attack_home" if self.position == 4 else "strength_defense_home"
            opponent_strength_type = "strength_defense_away" if self.position == 4 else "strength_attack_away"
        else:
            player_strength_type = "strength_attack_away" if self.position == 4 else "strength_defense_away"
            opponent_strength_type = "strength_defense_home" if self.position == 4 else "strength_attack_home"

        # Retrieve team strengths
        player_team_strength = getattr(team_data, player_strength_type, 1000)
        opponent_team_strength = getattr(
            opponent_team, opponent_strength_type, 1000)

        return (player_team_strength / opponent_team_strength)

    