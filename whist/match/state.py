"""Session-level state. One `MatchState` per session; many `GameState`s are
played over its lifetime (one per hand).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..game.player import Player, PlayerID
from ..game.ruleset import Ruleset
from ..game.state import GameState
from .scoreboard import Scoreboard
from .session import SessionConfig


@dataclass
class MatchState:
    registered: tuple[Player, ...] = ()
    scoreboard: Scoreboard = field(default_factory=Scoreboard)
    ruleset: Ruleset = field(default_factory=Ruleset.default)
    session_config: SessionConfig = field(default_factory=SessionConfig)
    hand_count: int = 0
    current_hand: GameState | None = None
    next_dealer: Player | None = None
    next_sitting_out: frozenset[Player] = frozenset()

    def register_players(self, players: list[Player]) -> None:
        self.registered = tuple(players)
        for p in players:
            self.scoreboard.register(p)

    @property
    def players(self) -> list[PlayerID]:
        return list(self.scoreboard.totals.keys())
