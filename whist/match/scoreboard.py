"""Running totals across hands in a match."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..game.player import Player, PlayerID
from ..game.scoring import Score


@dataclass
class Scoreboard:
    totals: dict[PlayerID, Score] = field(default_factory=dict)

    def register(self, player: Player) -> None:
        if player.id not in self.totals:
            self.totals[player.id] = 0

    def apply_deltas(self, deltas: Mapping[int, int]) -> None:
        for pid, delta in deltas.items():
            self.totals[pid] = self.totals.get(pid, 0) + delta

    def standings(self) -> list[tuple[PlayerID, Score]]:
        return sorted(self.totals.items(), key=lambda kv: -kv[1])

    def to_dict(self) -> dict[str, Any]:
        return {"totals": {str(k): int(v) for k, v in self.totals.items()}}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Scoreboard:
        return cls(totals={int(k): int(v) for k, v in d["totals"].items()})
