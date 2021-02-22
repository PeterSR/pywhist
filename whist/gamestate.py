from dataclasses import dataclass
from typing import List

from .cards import Suit, Deck


@dataclass
class Player:
    pass






@dataclass
class GameState:
    players: List[Player]
    hands: dict
    trump: Suit
    partner: list
    deck: Deck

    turn: int  # Index in players

    bid: str

    mode: str



class GameStateView:
    """
    Represents one players view of the current state of the game.
    """

    def __init__(self, state, player):
        self.state = state
        self.player = player