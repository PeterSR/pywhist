from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, cast

from ..cards import Card, Deck, Suit, Trick
from .events import BaseEvent, event_from_dict
from .partners import Partners, TeamID
from .phase import Phase
from .player import Player


@dataclass(frozen=True, slots=True)
class GameState:
    """Immutable state of a single hand.

    All transitions go through `whist.game.reducer.apply`, which returns a
    new `GameState`. `Game.take_action` is a thin wrapper that reassigns
    `self.state` to the new value.

    `hands` and `trick_owner` are plain dicts (not `MappingProxyType`) so
    msgspec can serialize them without a helper. The frozen dataclass blocks
    field reassignment; mutating the contained dicts is a reducer-only
    operation and a programming error anywhere else.
    """

    players: tuple[Player, ...]
    dealer: Player | None = None
    bid_winner: Player | None = None
    hands: dict[Player, Deck] = field(default_factory=dict)
    trump: Suit = Suit.Unknown
    partner_ace: Suit = Suit.Unknown
    partner_ace_revealed: bool = False
    partners: Partners | None = None
    kitty: Deck | None = None
    pile: Deck = field(default_factory=Deck.empty_pile)
    pile_play: tuple[Player, ...] = ()
    tricks: tuple[Trick, ...] = ()
    trick_owner: dict[int, TeamID] = field(default_factory=dict)
    events: tuple[BaseEvent, ...] = ()
    turn: int = 0
    phase: Phase = Phase.DEALING

    @property
    def round(self) -> int:
        return len(self.tricks)

    @property
    def num_players(self) -> int:
        return len(self.players)

    @property
    def current_player(self) -> Player:
        return self.players[self.turn]

    def replace(self, **changes: Any) -> GameState:
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        """Full (non-redacted) state, suitable for persistence / RL replay.

        Unlike `GameStateView.serialize`, this exposes every hand and the
        full partner assignment. Do NOT send this to a client — use a
        `GameStateView` for that.
        """
        assert self.partners is not None
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
    def from_dict(cls, d: dict[str, Any]) -> GameState:
        players = tuple(Player.from_dict(p) for p in d["players"])
        by_id = {p.id: p for p in players}

        hands: dict[Player, Deck] = {
            by_id[int(pid)]: Deck.from_list(cards) for pid, cards in d["hands"].items()
        }
        pile = Deck.from_list(d["pile"], allow_reorder=False)
        pile_play = tuple(Player.from_dict(p) for p in d["pile_play"])
        tricks = tuple(
            cast(Trick, tuple(Card.from_dict(c) for c in trick)) for trick in d["tricks"]
        )
        trick_owner = {int(k): TeamID(int(v)) for k, v in d["trick_owner"].items()}
        partners = Partners.from_dict(list(players), d["partners"])
        events: tuple[BaseEvent, ...] = tuple(event_from_dict(e) for e in d["events"])

        dealer = Player.from_dict(d["dealer"]) if d.get("dealer") is not None else None
        bid_winner = Player.from_dict(d["bid_winner"]) if d.get("bid_winner") is not None else None

        return cls(
            players=players,
            dealer=dealer,
            bid_winner=bid_winner,
            hands=hands,
            trump=Suit.from_code(d["trump"]),
            partner_ace=Suit.from_code(d["partner_ace"]),
            partner_ace_revealed=bool(d["partner_ace_revealed"]),
            partners=partners,
            pile=pile,
            pile_play=pile_play,
            tricks=tricks,
            trick_owner=trick_owner,
            events=events,
            turn=int(d["turn"]),
            phase=Phase(d["phase"]),
        )


class GameStateView:
    """Per-player redacted view. Constructed on demand; not stored in state."""

    def __init__(self, state: GameState, player: Player) -> None:
        self.state = state
        self.player = player

    @property
    def turn(self) -> int:
        return self.state.turn

    @property
    def current_player(self) -> Player:
        return self.state.current_player

    @property
    def trump(self) -> Suit:
        return self.state.trump

    @property
    def partner_ace(self) -> Suit:
        return self.state.partner_ace

    @property
    def pile(self) -> Deck:
        return self.state.pile

    @property
    def hand(self) -> Deck:
        return self.state.hands[self.player]

    @property
    def other_players(self) -> dict[Player, Deck]:
        players = tuple(p for p in self.state.players if p != self.player)
        return {p: Deck([Card.unknown] * len(self.state.hands[p].cards)) for p in players}

    @property
    def partners(self) -> tuple[Player, ...]:
        if not self.state.partner_ace_revealed:
            return ()
        assert self.state.partners is not None
        team_id = self.state.partners.team_id(self.player)
        members = self.state.partners.team_members(team_id)
        members.remove(self.player)
        return tuple(members)

    def serialize(self, event_cursor: int = 0) -> dict[str, Any]:
        """Per-player redacted view.

        Exposes:
          - phase, trump, partner_ace (+ revealed flag), dealer, bid_winner
          - own hand fully; other players' hand *sizes* only
          - public pile, pile_play order, collected tricks, trick_owner map
          - partners *only if* `partner_ace_revealed` — via `self.partners`
          - event log from `event_cursor` onward

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
