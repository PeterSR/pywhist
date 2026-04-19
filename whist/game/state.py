from dataclasses import dataclass
from typing import Any, cast

from ..cards import Card, Deck, Suit, Trick
from .events import BaseEvent, event_from_dict
from .partners import Partners, TeamID
from .phase import Phase
from .player import Player


@dataclass
class GameState:
    """
    Represents the state of a single game (dealing, bidding and 13 tricks)
    """

    dealer: Player = None
    bid_winner: Player = None
    players: list[Player] = None
    hands: dict[Player, Deck] = None
    trump: Suit = Suit.Unknown
    partner_ace: Suit = Suit.Unknown
    partner_ace_revealed: bool = False
    partners: Partners = None
    kitty: Deck = None
    pile: Deck = None
    pile_play: list[Player] = None
    tricks: list[Trick] = None
    trick_owner: dict[int, TeamID] = None

    events: list[BaseEvent] = None

    # Index in players
    turn: int = 0

    phase: Phase = Phase.DEALING

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

    def to_dict(self) -> dict[str, Any]:
        """Full (non-redacted) state, suitable for persistence / RL replay.

        Unlike `GameStateView.serialize`, this exposes every hand and the
        full partner assignment. Do NOT send this to a client — use a
        `GameStateView` for that.
        """
        return {
            "phase": self.phase.value,
            "trump": self.trump.code,
            "partner_ace": self.partner_ace.code,
            "partner_ace_revealed": self.partner_ace_revealed,
            "dealer": self.dealer.to_dict() if self.dealer is not None else None,
            "bid_winner": self.bid_winner.to_dict() if self.bid_winner is not None else None,
            "players": [p.to_dict() for p in self.players],
            "turn": self.turn,
            "hands": {str(p.id): self.hands[p].to_list() for p in self.players},
            "pile": self.pile.to_list(),
            "pile_play": [p.to_dict() for p in self.pile_play],
            "tricks": [[c.to_dict() for c in trick] for trick in self.tricks],
            "trick_owner": {str(k): int(v) for k, v in self.trick_owner.items()},
            "partners": self.partners.to_dict(),
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GameState":
        players = [Player.from_dict(p) for p in d["players"]]
        by_id = {p.id: p for p in players}

        hands: dict[Player, Deck] = {
            by_id[int(pid)]: Deck.from_list(cards) for pid, cards in d["hands"].items()
        }
        pile = Deck.from_list(d["pile"], allow_reorder=False)
        pile_play = [Player.from_dict(p) for p in d["pile_play"]]
        tricks = [cast(Trick, tuple(Card.from_dict(c) for c in trick)) for trick in d["tricks"]]
        trick_owner = {int(k): TeamID(int(v)) for k, v in d["trick_owner"].items()}
        partners = Partners.from_dict(players, d["partners"])
        events: list[BaseEvent] = [event_from_dict(e) for e in d["events"]]

        dealer = Player.from_dict(d["dealer"]) if d.get("dealer") is not None else None
        bid_winner = Player.from_dict(d["bid_winner"]) if d.get("bid_winner") is not None else None

        state = cls.__new__(cls)
        state.dealer = dealer
        state.bid_winner = bid_winner
        state.players = players
        state.hands = hands
        state.trump = Suit.from_code(d["trump"])
        state.partner_ace = Suit.from_code(d["partner_ace"])
        state.partner_ace_revealed = bool(d["partner_ace_revealed"])
        state.partners = partners
        state.pile = pile
        state.pile_play = pile_play
        state.tricks = tricks
        state.trick_owner = trick_owner
        state.events = events
        state.turn = int(d["turn"])
        state.phase = Phase(d["phase"])
        # Not persisted across roundtrip yet:
        state.kitty = None
        return state


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
        players = tuple(p for p in self.state.players if p != self.player)

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

    def serialize(self, event_cursor: int = 0) -> dict[str, Any]:
        """Per-player redacted view.

        Exposes:
          - phase, trump, partner_ace (+ revealed flag), dealer, bid_winner
          - own hand fully; other players' hand *sizes* only (cards redacted
            via `Card.unknown` in `other_players`)
          - public pile, pile_play order, collected tricks, trick_owner map
          - partners *only if* `partner_ace_revealed` — via `self.partners`
          - full event log from `event_cursor` onward

        `event_cursor` lets a client poll incrementally: pass the
        `event_cursor_next` from the previous call. Default 0 = full log.
        """
        s = self.state
        return {
            "phase": s.phase.value,
            "trump": s.trump.code,
            "partner_ace": s.partner_ace.code,
            "partner_ace_revealed": s.partner_ace_revealed,
            "dealer": s.dealer.to_dict() if s.dealer is not None else None,
            "bid_winner": s.bid_winner.to_dict() if s.bid_winner is not None else None,
            "players": [p.to_dict() for p in s.players],
            "turn": s.turn,
            "current_player": s.current_player.to_dict(),
            "pov_player": self.player.to_dict(),
            "hand": self.hand.to_list(),
            "other_hand_sizes": {
                str(p.id): len(s.hands[p].cards) for p in s.players if p != self.player
            },
            "pile": s.pile.to_list(),
            "pile_play": [p.to_dict() for p in s.pile_play],
            "tricks": [[c.to_dict() for c in trick] for trick in s.tricks],
            "trick_owner": {str(k): int(v) for k, v in s.trick_owner.items()},
            "partners_revealed": [p.to_dict() for p in self.partners],
            "events": [e.to_dict() for e in s.events[event_cursor:]],
            "event_cursor_next": len(s.events),
        }
