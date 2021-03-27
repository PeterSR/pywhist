from dataclasses import dataclass
from typing import List, Dict

from .cards import Suit, Card, Deck


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
    tricks: List[Deck] = None

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

    @property
    def pile(self):
        return self.state.pile

    @property
    def hand(self):
        return self.state.hands[self.player]

    @property
    def other_players(self):
        players = tuple(p for p in self.state.players if p is not self.player)

        hands = {}

        for p in players:
            num_cards = len(self.state.hands[p].cards)
            hands[p] = Deck([Card.unknown] * num_cards)

        return hands
