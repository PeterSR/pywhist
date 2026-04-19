from collections import defaultdict
from dataclasses import dataclass, field
from itertools import count
from typing import NewType

from .player import Player

Team = list[Player]
TeamID = NewType("TeamID", int)

_team_id_counter = count(1)


def _fresh_team_id() -> TeamID:
    """Return a process-unique `TeamID`. Used to seed singleton teams."""
    return TeamID(next(_team_id_counter))


@dataclass
class Partners:
    players: list[Player]
    team_id_assignment: dict[Player, TeamID] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.team_id_assignment:
            # Give each player their own team
            self.team_id_assignment = {player: _fresh_team_id() for player in self.players}

    def join(self, *players: Player) -> None:
        if len(players) == 0:
            return

        if len(players) > len(self.players):
            raise ValueError("Cannot join more players than there exists.")

        first_player = players[0]
        team_id = self.team_id(first_player)

        for player in players:
            self.team_id_assignment[player] = team_id

    def isolate(self, player: Player) -> None:
        rest_of_players = [p for p in self.players if p != player]
        self.join(*rest_of_players)

    def bisect(self, *team_1_players: Player) -> None:
        team_2_players = [p for p in self.players if p not in team_1_players]
        self.join(*team_1_players)
        self.join(*team_2_players)

    def team_id(self, player: Player) -> TeamID:
        return self.team_id_assignment[player]

    def team_members(self, team_id: TeamID) -> Team:
        return [player for player in self.players if self.team_id(player) == team_id]

    def team_size(self, team_id: TeamID) -> int:
        return len(self.team_members(team_id))

    @property
    def teams(self) -> dict[TeamID, Team]:
        d: defaultdict[TeamID, Team] = defaultdict(list)
        for player in self.players:
            team_id = self.team_id(player)
            d[team_id].append(player)
        return dict(d)

    @property
    def team_ids(self) -> set[TeamID]:
        return {self.team_id(player) for player in self.players}

    @property
    def num_teams(self) -> int:
        return len(self.team_ids)
