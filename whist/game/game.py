from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import product
from random import Random
from typing import Any, ClassVar

from ..cards import Card, Deck, Rank, Suit, suits
from ..errors import IllegalPhase
from .actions import (
    BanketAction,
    BanketSkipAction,
    BaseAction,
    BidAction,
    CallAction,
    DetKanJegSelvAction,
    GaaMedAction,
    JernhaandAction,
    JernhaandDeclineAction,
    KingCallAction,
    PassAction,
    PlayAction,
    ReBanketAction,
)
from .bids import BID_LADDER, BidModifier, Call, NoloBid, NumberBid, bid_rank
from .partners import Partners, TeamID
from .phase import Phase
from .player import Player, create_default_players
from .reducer import apply, perform_deal
from .ruleset import Ruleset
from .state import GameState


@dataclass
class Game:
    """Ergonomic mutating wrapper over the pure reducer.

    `Game` keeps a single `GameState` that it replaces atomically on each
    `take_action`. The underlying transition is computed by `reducer.apply`,
    so test code and RL training can skip the wrapper and call `apply`
    directly for deterministic replay.
    """

    state: GameState | None = None
    ruleset: Ruleset | None = None
    seed: int | None = None
    _rng: Random = field(default_factory=Random, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.ruleset is None:
            self.ruleset = Ruleset.default()
        if self.seed is not None:
            self._rng = Random(self.seed)
        if self.state is None:
            self.state = self.initial_state()

    def initial_state(self, **settings: Any) -> GameState:
        players_list = settings.get("players")

        if players_list is None:
            players_list = create_default_players()

        players: tuple[Player, ...] = tuple(players_list)
        hands = {p: Deck.empty() for p in players}
        partners = Partners(list(players))

        dealer_index = int(settings.get("dealer_index", 0))
        dealer = players[dealer_index]

        turn = int(settings.get("turn", 0))

        assert self.ruleset is not None
        return GameState(
            players=players,
            variant=self.ruleset.variant,
            dealer=dealer,
            hands=hands,
            partners=partners,
            turn=turn,
            seed=self.seed,
        )

    def deal(self) -> None:
        assert self.state is not None
        new_state, events = perform_deal(self.state, rng=self._rng)
        self.state = new_state.replace(events=(*self.state.events, *events))

    @property
    def has_ended(self) -> bool:
        assert self.state is not None
        hand_size = 13
        return len(self.state.tricks) >= hand_size

    @property
    def current_player(self) -> Player:
        assert self.state is not None
        return self.state.current_player

    @property
    def bid_winner(self) -> Player | None:
        """Kept for back-compat — `state.bid_winner` is the source of truth."""
        assert self.state is not None
        return self.state.bid_winner

    def valid_actions(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        state = self.state

        if player != self.current_player:
            # DEALING-with-jernhaand is the one phase where non-current players
            # may still act (anyone eligible can declare).
            if state.phase == Phase.DEALING and player in state.jernhaand_pending:
                return [JernhaandDeclineAction(player), JernhaandAction(player)]
            return []

        handler = self._VALID_ACTIONS_DISPATCH.get(state.phase)
        if handler is None:
            raise IllegalPhase(f"valid_actions: no dispatch for phase {state.phase!r}")
        return handler(self, player)

    # ---- per-phase helpers -------------------------------------------

    def _valid_actions_dealing(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        if player in self.state.jernhaand_pending:
            return [JernhaandDeclineAction(player), JernhaandAction(player)]
        return []

    def _valid_actions_bidding(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        state = self.state
        a = state.auction

        actions: list[BaseAction] = []

        in_tilbage = (
            a.top_bid is not None
            and a.top_bidder != player
            and any(bidder == player for bidder, _ in a.bids)
            and player not in a.passed
        )

        if in_tilbage:
            # Tilbage: pass first (yield), then det-kan-jeg-selv, then overcalls.
            actions.append(PassAction())
            actions.append(DetKanJegSelvAction())
            actions.extend(self._enumerate_higher_bids(a.top_bid))
            return actions

        if a.top_bid is None:
            # Opening bidder — encourage a bid as actions[0] so the auction
            # doesn't all-pass into a redeal loop under smoke-test drivers.
            actions.append(BidAction(NumberBid(7, BidModifier.GODE), trump=None))
            actions.append(PassAction())
            actions.extend(self._enumerate_higher_bids(None)[1:])  # drop duplicate first
            return actions

        # Forward bidder against an existing top bid: pass first (keeps
        # smoke-tests from overcalling forever), then overcalls.
        actions.append(PassAction())
        if isinstance(a.top_bid, (NumberBid, NoloBid)):
            if isinstance(a.top_bid, NumberBid) and a.top_bid.modifier == BidModifier.VIP:
                actions.append(GaaMedAction())
            if isinstance(a.top_bid, NoloBid):
                actions.append(GaaMedAction())
        actions.extend(self._enumerate_higher_bids(a.top_bid))
        return actions

    def _enumerate_higher_bids(self, top_bid: Any) -> list[BaseAction]:
        start = 0 if top_bid is None else bid_rank(top_bid) + 1
        out: list[BaseAction] = []
        for b in BID_LADDER[start:]:
            if isinstance(b, NumberBid) and b.modifier == BidModifier.ALMINDELIG:
                # Almindelig needs trump named. Expose one per non-clubs suit;
                # klør gets auto-rewritten to GODE by the reducer, so include
                # it for test coverage but skip for default ordering here.
                for trump in (Suit.Heart, Suit.Diamond, Suit.Spade, Suit.Club):
                    out.append(BidAction(b, trump=trump))
            else:
                out.append(BidAction(b, trump=None))
        return out

    def _valid_actions_calling(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        _ = player
        if self.state.king_call_required:
            # All (trump, king-suit) combos where trump != king_suit.
            calls: list[BaseAction] = []
            for trump, king in product(suits, suits):
                if trump == king:
                    continue
                calls.append(KingCallAction(trump=trump, king_suit=king))
            return calls

        return [
            CallAction(Call(trump, partner_ace))
            for trump, partner_ace in product(suits, suits)
            if trump != partner_ace
        ]

    def _valid_actions_banket(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        assert self.state.partners is not None
        declarer = self.state.bid_winner
        assert declarer is not None
        declarer_team = self.state.partners.team_id(declarer)
        player_team = self.state.partners.team_id(player)

        if player_team == declarer_team:
            # Declarer side: skip by default; re-banket only if a banket has landed.
            actions: list[BaseAction] = [BanketSkipAction()]
            if self.state.banket.banket_by is not None and self.state.banket.re_banket_by is None:
                actions.append(ReBanketAction())
            return actions

        # Opponent side: skip first, then optional banket.
        actions_opp: list[BaseAction] = [BanketSkipAction()]
        if self.state.banket.banket_by is None:
            actions_opp.append(BanketAction())
        return actions_opp

    def _valid_actions_playing(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        state = self.state
        hand = state.hands[player]
        pile = state.pile

        if len(pile) == 0:
            return [PlayAction(card) for card in hand]

        first_card = pile.cards[0]

        if first_card == Card.joker:
            suits_from_hand = list(hand)
        else:
            if first_card.suit == state.partner_ace:
                partner_ace = Card(state.partner_ace, Rank.Ace)
                if partner_ace in hand:
                    return [PlayAction(partner_ace)]

            suits_from_hand = [card for card in hand if card.suit is first_card.suit]

        if len(suits_from_hand) > 0:
            return [PlayAction(card) for card in suits_from_hand]
        return [PlayAction(card) for card in hand]

    @staticmethod
    def _valid_actions_none(_self: Game, _player: Player) -> list[BaseAction]:
        """Stub — phase has no player-facing actions yet."""
        return []

    _VALID_ACTIONS_DISPATCH: ClassVar[dict[Phase, Callable[[Game, Player], list[BaseAction]]]]

    def is_valid_action(self, player: Player, action: BaseAction) -> bool:
        if player != self.current_player:
            # Jernhaand exception: anyone eligible can declare.
            assert self.state is not None
            if self.state.phase == Phase.DEALING and isinstance(
                action, (JernhaandAction, JernhaandDeclineAction)
            ):
                return action.player in self.state.jernhaand_pending
            return False
        return action in self.valid_actions(player)

    def take_action(self, player: Player, action: BaseAction) -> bool:
        assert self.state is not None
        if not isinstance(action, BaseAction):
            raise TypeError(f"Not an action: {action}")

        new_state, _events = apply(self.state, action, rng=self._rng)
        self.state = new_state
        return True

    def get_scoreboard(self) -> dict[tuple[Player, ...], int]:
        assert self.state is not None
        assert self.state.partners is not None

        scores: Counter[TeamID] = Counter()
        for team_id in self.state.trick_owner.values():
            scores[team_id] += 1

        scoreboard: dict[tuple[Player, ...], int] = {}
        for team_id, score in scores.items():
            members = tuple(self.state.partners.team_members(team_id))
            scoreboard[members] = score

        return scoreboard


# Populate dispatch table after class body (ClassVar → @dataclass skips it).
Game._VALID_ACTIONS_DISPATCH = {
    Phase.DEALING: Game._valid_actions_dealing,
    Phase.BIDDING: Game._valid_actions_bidding,
    Phase.BANKET: Game._valid_actions_banket,
    Phase.CALLING: Game._valid_actions_calling,
    Phase.PLAYING: Game._valid_actions_playing,
    Phase.KATTEN_EXCHANGE: Game._valid_actions_none,
    Phase.VIP_FLIP: Game._valid_actions_none,
    Phase.HALVE_TRUMP: Game._valid_actions_none,
    Phase.MARKER_PLACEMENT: Game._valid_actions_none,
    Phase.SCORING: Game._valid_actions_none,
    Phase.FINISHED: Game._valid_actions_none,
}
