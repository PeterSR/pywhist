from dataclasses import dataclass
from typing import List, Dict

from ..cards import Suit, Card, Deck, Trick
from .player import Player
from .partners import Partners, TeamID
from .events import BaseEvent


@dataclass
class GameState:
    """
    Represents the state of a single game (dealing, bidding and 13 tricks)
    """

    dealer: Player = None
    bid_winner: Player = None
    players: List[Player] = None
    hands: Dict[Player, Deck] = None
    trump: Suit = Suit.Unknown
    partner_ace: Suit = Suit.Unknown
    partner_ace_revealed: bool = False
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

    phase: str = "dealing"

    def __post_init__(self):
        self.round_reset()
        self.tricks = []
        self.trick_owner = {}
        self.events = []

        if self.partners is None:
            self.partners = Partners(self.players)

    @property
    def round(self):
        return len(self.tricks)

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
    def turn(self):
        return self.state.turn

    @property
    def current_player(self):
        return self.state.current_player

    @property
    def trump(self):
        return self.state.trump

    @property
    def partner_ace(self):
        return self.state.partner_ace

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

    @property
    def partners(self):
        if not self.state.partner_ace_revealed:
            return tuple([])
        team_id = self.state.partners.team_id(self.player)
        members = self.state.partners.team_members(team_id)
        members.remove(self.player)
        return tuple(members)

    def serialize(self):
        return {
            "turn": self.turn,
            "current_player": self.current_player.serialize(),
            "pov_player": self.player.serialize(),
            "trump": self.trump.name,
        }
