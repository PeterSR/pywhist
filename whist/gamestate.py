from dataclasses import dataclass
from typing import List, Dict

from .cards import Suit, Card, Deck, Trick
from .player import Player
from .partners import Partners, TeamID
from .game_events import BaseEvent


@dataclass
class GameState:
    players: List[Player] = None
    hands: Dict[Player, Deck] = None
    trump: Suit = Suit.Unknown
    partners: Partners = None
    kitty: Deck = None
    pile: Deck = None
    pile_play: List[Player] = None
    tricks: List[Trick] = None
    trick_owner: Dict[int, TeamID] = None

    events: List[BaseEvent] = None

    # Index in players
    turn: int = 0

    bid: str = ""

    mode: str = ""

    def __post_init__(self):
        self.round_reset()
        self.tricks = []
        self.trick_owner = {}
        self.events = []

        if self.partners is None:
            self.partners = Partners(self.players)

    @property
    def num_players(self):
        return len(self.players)

    @property
    def current_player(self):
        return self.players[self.turn]

    def round_reset(self):
        self.pile = Deck.empty_pile()
        self.pile_play = []


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
