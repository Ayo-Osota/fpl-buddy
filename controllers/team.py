class Team:
    def __init__(self, team_data):
        self.code = team_data.get("code")
        self.name = team_data.get("name")
        self.short_name = team_data.get("short_name")
        self.strength = team_data.get("strength")
        self.strength_overall_home = team_data.get("strength_overall_home")
        self.strength_overall_away = team_data.get("strength_overall_away")
        self.strength_attack_home = team_data.get("strength_attack_home")
        self.strength_attack_away = team_data.get("strength_attack_away")
        self.strength_defence_home = team_data.get("strength_defence_home")
        self.strength_defence_away = team_data.get("strength_defence_away")


def get_team(opponent_id, teams_list):
    """
    Retrieve the opponent team from a list of teams based on the opponent ID.

    :param opponent_id: The ID of the opponent team to find.
    :param teams_list: A list of Team objects to search through.
    :return: The opponent Team object if found, otherwise None.
    """
    for team in teams_list:
        if team.id == opponent_id:
            return team
    return None
