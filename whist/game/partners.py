from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, NewType

from .player import Player

Team = list[Player]
TeamID = NewType("TeamID", int)


@dataclass
class Partners:
    players: list[Player]
    team_id_assignment: dict[Player, TeamID] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.team_id_assignment:
            # Seed each player into their own singleton team, keyed by the
            # player's id. Deterministic across processes — no global counter.
            # Post-`bisect`/`join` the surviving team ids are the min
            # player-id in each resulting team.
            self.team_id_assignment = {player: TeamID(player.id) for player in self.players}

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

    def bisected(self, *team_1_players: Player) -> "Partners":
        """Non-mutating variant of `bisect` used by the pure reducer."""
        new = Partners(list(self.players), dict(self.team_id_assignment))
        new.bisect(*team_1_players)
        return new

    def isolated(self, player: Player) -> "Partners":
        """Non-mutating variant of `isolate` used by the pure reducer."""
        new = Partners(list(self.players), dict(self.team_id_assignment))
        new.isolate(player)
        return new

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "players": [p.id for p in self.players],
            "team_of": {str(p.id): int(tid) for p, tid in self.team_id_assignment.items()},
        }

    @classmethod
    def from_dict(cls, players: list[Player], d: Mapping[str, Any]) -> "Partners":
        by_id = {p.id: p for p in players}
        ordered = [by_id[int(pid)] for pid in d["players"]]
        assignment = {by_id[int(pid)]: TeamID(int(tid)) for pid, tid in d["team_of"].items()}
        return cls(ordered, assignment)
