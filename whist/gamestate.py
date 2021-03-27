from dataclasses import dataclass
from typing import List, Dict

from .cards import Suit, Deck


PlayerID = int

@dataclass(frozen=True)
class Player:
    id: PlayerID
    name: str






@dataclass
class GameState:
    players: List[Player] = None
    hands: Dict[Player, Deck] = None
    trump: Suit = Suit.Unknown
    partner: list = None
    kitty: Deck = Deck.empty()
    pile: Deck = Deck.empty()

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