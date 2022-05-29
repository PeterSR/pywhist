from typing import List
from dataclasses import dataclass

from ..game.player import PlayerID
from ..game.state import GameState
from .scoreboard import Scoreboard


@dataclass
class MatchState:
    """
    Represents the state for a match of n games
    """

    game_state: GameState = None
    game_count: int = 0
    max_game_count: int = -1  # -1 for infinite
    scoreboard: Scoreboard = None

    def __post_init__(self):
        if self.scoreboard is None:
            self.scoreboard = dict()

    @property
    def players(self) -> List[PlayerID]:
        return list(self.scoreboard.keys())