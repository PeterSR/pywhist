from collections import defaultdict
from dataclasses import dataclass, field

from .player import Player

Team = list[Player]
TeamID = int


@dataclass
class Partners:
    players: list[Player]
    team_id_assignment: dict[Player, TeamID] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.team_id_assignment:
            # Give each player their own team
            self.team_id_assignment = {
                player: self.initial_team_assignment(i) for i, player in enumerate(self.players)
            }

    def initial_team_assignment(self, index):
        offset = 1000
        return index + offset

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
        rest_of_players = [p for p in self.players if p != player]
        self.join(*rest_of_players)

    def bisect(self, *team_1_players):
        team_2_players = [p for p in self.players if p not in team_1_players]
        self.join(*team_1_players)
        self.join(*team_2_players)

    def team_id(self, player: Player):
        return self.team_id_assignment[player]

    def team_members(self, team_id: TeamID) -> Team:
        return [player for player in self.players if self.team_id(player) == team_id]

    def team_size(self, team_id: TeamID):
        return len(self.team_members(team_id))

    @property
    def teams(self):
        d = defaultdict(list)
        for player in self.players:
            team_id = self.team_id(player)
            d[team_id].append(player)
        return dict(d)

    @property
    def team_ids(self):
        return set(self.team_id(player) for player in self.players)

    @property
    def num_teams(self):
        return len(self.team_ids)
