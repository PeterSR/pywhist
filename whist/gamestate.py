from dataclasses import dataclass
from typing import List

from .cards import Suit, Deck


@dataclass
class Player:
    pass






@dataclass
class GameState:
    players: List[Player] = None
    hands: dict = None
    trump: Suit = Suit.Unknown
    partner: list = None
    deck: Deck = Deck.sorted()

    # Index in players
    turn: int = 0

    bid: str = ""

    mode: str = ""



class GameStateView:
    """
    Represents one players view of the current state of the game.
    """

    def __init__(self, state, player):
        self.state = state
        self.player = player