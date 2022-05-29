from dataclasses import dataclass

from ..game.state import GameState
from .scoreboard import Scoreboard


@dataclass
class MatchState:
    """
    Represents the state for a match of n games
    """

    game_state: GameState = None
    game_count: int = 0
    scoreboard: Scoreboard = None

    def __post_init__(self):
        if self.scoreboard is None:
            self.scoreboard = dict()