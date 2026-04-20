from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any, cast

from ..cards import Card, Deck, Suit, Trick
from .bids import Bid, bid_from_dict, bid_to_dict
from .events import BaseEvent, event_from_dict
from .partners import Partners, TeamID
from .phase import Phase
from .player import Player


@dataclass(frozen=True, slots=True)
class AuctionState:
    """Running state of the auction while `phase == Phase.BIDDING`.

    `passed` excludes `gaa_med` members — gå-med players forfeit the right
    to overcall but aren't "passed" in the sense of being out of the
    contract.
    """

    bids: tuple[tuple[Player, Bid], ...] = ()
    passed: frozenset[Player] = frozenset()
    current_bidder: Player | None = None
    top_bid: Bid | None = None
    top_bidder: Player | None = None
    gaa_med: tuple[Player, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "bids": [[p.to_dict(), bid_to_dict(b)] for p, b in self.bids],
            "passed": [p.to_dict() for p in self.passed],
            "current_bidder": (
                self.current_bidder.to_dict() if self.current_bidder is not None else None
            ),
            "top_bid": bid_to_dict(self.top_bid) if self.top_bid is not None else None,
            "top_bidder": self.top_bidder.to_dict() if self.top_bidder is not None else None,
            "gaa_med": [p.to_dict() for p in self.gaa_med],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> AuctionState:
        return cls(
            bids=tuple(
                (Player.from_dict(entry[0]), bid_from_dict(entry[1])) for entry in d["bids"]
            ),
            passed=frozenset(Player.from_dict(p) for p in d["passed"]),
            current_bidder=(
                Player.from_dict(d["current_bidder"])
                if d.get("current_bidder") is not None
                else None
            ),
            top_bid=bid_from_dict(d["top_bid"]) if d.get("top_bid") is not None else None,
            top_bidder=(
                Player.from_dict(d["top_bidder"]) if d.get("top_bidder") is not None else None
            ),
            gaa_med=tuple(Player.from_dict(p) for p in d["gaa_med"]),
        )


@dataclass(frozen=True, slots=True)
class KattenState:
    """Running state during KATTEN_EXCHANGE (and VIP_FLIP reveals)."""

    cards: tuple[Card, ...] = ()
    flipped: tuple[bool, ...] = ()
    holder: Player | None = None  # player currently holding the katten (post-take)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cards": [c.to_dict() for c in self.cards],
            "flipped": list(self.flipped),
            "holder": self.holder.to_dict() if self.holder is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> KattenState:
        return cls(
            cards=tuple(Card.from_dict(c) for c in d["cards"]),
            flipped=tuple(bool(v) for v in d["flipped"]),
            holder=Player.from_dict(d["holder"]) if d.get("holder") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class BidWhistAuctionState:
    """Running state of the bid-whist auction while `phase == Phase.BIDDING`.

    Records each seat's bid or pass. `top_level` + `top_trump` describe the
    current leading bid; `top_trump is None` means no-trump.
    """

    bids: tuple[tuple[Player, int, str | None], ...] = ()  # (player, level, trump_code_or_None)
    passed: frozenset[Player] = frozenset()
    current_bidder: Player | None = None
    top_level: int | None = None
    top_trump: str | None = None
    top_bidder: Player | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "bids": [[p.to_dict(), level, trump] for p, level, trump in self.bids],
            "passed": [p.to_dict() for p in self.passed],
            "current_bidder": (
                self.current_bidder.to_dict() if self.current_bidder is not None else None
            ),
            "top_level": self.top_level,
            "top_trump": self.top_trump,
            "top_bidder": self.top_bidder.to_dict() if self.top_bidder is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BidWhistAuctionState:
        return cls(
            bids=tuple(
                (Player.from_dict(entry[0]), int(entry[1]), entry[2]) for entry in d["bids"]
            ),
            passed=frozenset(Player.from_dict(p) for p in d["passed"]),
            current_bidder=(
                Player.from_dict(d["current_bidder"])
                if d.get("current_bidder") is not None
                else None
            ),
            top_level=int(d["top_level"]) if d.get("top_level") is not None else None,
            top_trump=d.get("top_trump"),
            top_bidder=(
                Player.from_dict(d["top_bidder"]) if d.get("top_bidder") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class BanketState:
    """Banket / re-banket flags for the active contract."""

    banket_by: Player | None = None
    re_banket_by: Player | None = None
    # Players who've already passed on banket — they get one chance.
    declined: frozenset[Player] = frozenset()

    @property
    def multiplier(self) -> int:
        if self.re_banket_by is not None:
            return 4
        if self.banket_by is not None:
            return 2
        return 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "banket_by": self.banket_by.to_dict() if self.banket_by is not None else None,
            "re_banket_by": (
                self.re_banket_by.to_dict() if self.re_banket_by is not None else None
            ),
            "declined": [p.to_dict() for p in self.declined],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BanketState:
        return cls(
            banket_by=(
                Player.from_dict(d["banket_by"]) if d.get("banket_by") is not None else None
            ),
            re_banket_by=(
                Player.from_dict(d["re_banket_by"]) if d.get("re_banket_by") is not None else None
            ),
            declined=frozenset(Player.from_dict(p) for p in d.get("declined", [])),
        )


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
    # Which rule variant the reducer should dispatch to. The string is the
    # value of `ruleset.Variant`; kept as a plain str here to avoid a circular
    # import between state.py and ruleset.py.
    variant: str = "esmakker"
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
    auction: AuctionState = field(default_factory=AuctionState)
    banket: BanketState = field(default_factory=BanketState)
    jernhaand_pending: frozenset[Player] = frozenset()
    # Declarer holds all 4 aces → next post-auction action is KingCallAction
    # instead of CallAction. Set by the reducer when the bid closes.
    king_call_required: bool = False
    seed: int | None = None
    katten: KattenState = field(default_factory=KattenState)
    marker_card: Card | None = None
    # Cards permanently out of play for the hand (post-katten discards).
    discarded: tuple[Card, ...] = ()
    # Players whose hands are face-up (Bordlægger after trick 1 collection).
    hand_exposed: frozenset[Player] = frozenset()
    # Bid-whist auction state. Populated only while `variant == "bid_whist"`.
    bid_whist_auction: BidWhistAuctionState = field(default_factory=BidWhistAuctionState)
    # Queue of remaining katten exchangers (after the current one). Populated
    # for nolo contracts with gå-med players; empty for a single-exchanger
    # katten. FIFO — head becomes the next exchanger after the current one
    # finishes (skip or take+discard). Each exchanger sees the discards of
    # the previous exchanger as their katten.
    katten_cycle: tuple[Player, ...] = ()
    # Queue of gå-med players still to be polled after the latest Vip flip.
    # Head = current polling candidate; when empty, control returns to
    # declarer. A takeover by any candidate ends the cycle immediately.
    vip_poll_queue: tuple[Player, ...] = ()

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
            "variant": self.variant,
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
            "auction": self.auction.to_dict(),
            "banket": self.banket.to_dict(),
            "jernhaand_pending": [p.to_dict() for p in self.jernhaand_pending],
            "king_call_required": self.king_call_required,
            "seed": self.seed,
            "katten": self.katten.to_dict(),
            "marker_card": self.marker_card.to_dict() if self.marker_card is not None else None,
            "discarded": [c.to_dict() for c in self.discarded],
            "hand_exposed": [p.to_dict() for p in self.hand_exposed],
            "bid_whist_auction": self.bid_whist_auction.to_dict(),
            "katten_cycle": [p.to_dict() for p in self.katten_cycle],
            "vip_poll_queue": [p.to_dict() for p in self.vip_poll_queue],
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

        auction = AuctionState.from_dict(d["auction"]) if "auction" in d else AuctionState()
        banket = BanketState.from_dict(d["banket"]) if "banket" in d else BanketState()
        jernhaand_pending = frozenset(Player.from_dict(p) for p in d.get("jernhaand_pending", []))
        seed_val = d.get("seed")
        katten = KattenState.from_dict(d["katten"]) if "katten" in d else KattenState()
        marker_card = Card.from_dict(d["marker_card"]) if d.get("marker_card") else None
        discarded = tuple(Card.from_dict(c) for c in d.get("discarded", []))
        hand_exposed = frozenset(Player.from_dict(p) for p in d.get("hand_exposed", []))
        bid_whist_auction = (
            BidWhistAuctionState.from_dict(d["bid_whist_auction"])
            if "bid_whist_auction" in d
            else BidWhistAuctionState()
        )
        katten_cycle = tuple(Player.from_dict(p) for p in d.get("katten_cycle", []))
        vip_poll_queue = tuple(Player.from_dict(p) for p in d.get("vip_poll_queue", []))

        return cls(
            players=players,
            variant=d.get("variant", "esmakker"),
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
            auction=auction,
            banket=banket,
            jernhaand_pending=jernhaand_pending,
            king_call_required=bool(d.get("king_call_required", False)),
            seed=int(seed_val) if seed_val is not None else None,
            katten=katten,
            marker_card=marker_card,
            discarded=discarded,
            hand_exposed=hand_exposed,
            bid_whist_auction=bid_whist_auction,
            katten_cycle=katten_cycle,
            vip_poll_queue=vip_poll_queue,
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
            "exposed_hands": {
                str(p.id): s.hands[p].to_list() for p in s.hand_exposed if p != self.player
            },
            "pile": s.pile.to_list(),
            "pile_play": [p.to_dict() for p in s.pile_play],
            "tricks": [[c.to_dict() for c in trick] for trick in s.tricks],
            "trick_owner": {str(k): int(v) for k, v in s.trick_owner.items()},
            "partners_revealed": [p.to_dict() for p in self.partners],
            "events": [e.to_dict() for e in s.events[event_cursor:]],
            "event_cursor_next": len(s.events),
        }
