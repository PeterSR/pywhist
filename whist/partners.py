from dataclasses import dataclass
from typing import List, Dict

from .player import Player


TeamID = int


@dataclass
class Partners:
    players: List[Player]
    team_id_assignment: Dict[Player, TeamID] = None

    def __post_init__(self):
        if self.team_id_assignment is None:
            # Give each player their own team
            self.team_id_assignment = {
                player: i
                for i, player in enumerate(self.players)
            }

    def join(self, *players):
        if len(players) == 0:
            return

        if len(players) > len(self.players):
            raise ValueError("Cannot join more players than there exists.")

        first_player = players[0]
        team_id = self.team_id(first_player)

        for player in players:
            self.team_id_assignment[player] = team_id

    def isolate(self, player):
        rest_of_players = [
            p for p in self.players
            if p != player
        ]
        self.join(*rest_of_players)

    def bisect(self, *team_1_players):
        team_2_players = [
            p for p in self.players
            if p not in team_1_players
        ]
        self.join(*team_1_players)
        self.join(*team_2_players)

    def team_id(self, player):
        return self.team_id_assignment[player]

    def team_members(self, team_id):
        return [
            player
            for player in self.players
            if self.team_id(player) == team_id
        ]

    def team_size(self, team_id):
        return len(self.team_members(team_id))

    @property
    def teams(self):
        return set(
            self.team_id(player)
            for player in self.players
        )

    @property
    def num_teams(self):
        return len(self.teams)
