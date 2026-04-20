"""Bid whist (American partnership whist with bidding).

Four players, fixed partnerships (seats 0+2 vs 1+3). Each player is dealt 13
cards from a standard 52-card deck. Auction: starting at forhand, each seat
either bids `(level, trump | no-trump)` strictly higher than the current top
or passes. The auction closes when three players have passed; the highest
bidder becomes declarer, sets trump, and leads the first trick. Declarer's
side must take at least `(6 + level)` tricks ("making the bid"); otherwise
they are "set" and pay the level instead.

The canonical kitty exchange is not modelled here; the 52-card no-kitty
variant is a common simplification and keeps the variant self-contained.
"""

from __future__ import annotations

from random import Random

from ...cards import Deck, Suit
from ...errors import IllegalAction, RulesViolation
from ..actions import BaseAction, BidWhistBidAction, PassAction, PlayAction
from ..events import (
    ActionTakenEvent,
    BaseEvent,
    BidWhistBidMadeEvent,
    BidWhistBidWonEvent,
    DealEvent,
    PartnerRevealedEvent,
    PhaseTransitionEvent,
    ScoreEvent,
    TrickTakenEvent,
)
from ..partners import Partners, TeamID
from ..phase import Phase
from ..player import Player
from ..state import BidWhistAuctionState, GameState
from ..tableround import TableRound
from ._base import (
    PhaseHandler,
    _assign_trick,
    _deck_with_card,
    _deck_without,
    _score_pile,
)

# No-trump is encoded as `trump == Suit.Unknown` on the game state.


# ---- deal ----------------------------------------------------------------


def _perform_deal(state: GameState, *, rng: Random) -> tuple[GameState, tuple[BaseEvent, ...]]:
    assert state.dealer is not None
    if len(state.players) != 4:
        raise IllegalAction("bid whist deal expects exactly 4 players")

    deck = Deck.full_deck(num_jokers=0)
    deck.shuffle(rng=rng)

    order = list(TableRound(state.dealer, list(state.players)))
    hands: dict[Player, list] = {p: [] for p in state.players}  # type: ignore[type-arg]
    for i, card in enumerate(deck.cards):
        hands[order[i % 4]].append(card)

    sorted_hands: dict[Player, Deck] = {}
    for p, cards in hands.items():
        d = Deck(cards)
        d.sort()
        sorted_hands[p] = d

    partners = Partners(list(state.players))
    partners.bisect(state.players[0], state.players[2])

    forhand = order[0]
    auction = BidWhistAuctionState(current_bidder=forhand)

    events: tuple[BaseEvent, ...] = (
        DealEvent(dealer=state.dealer, seed=state.seed),
        PartnerRevealedEvent(declarer=state.players[0], partner=state.players[2]),
        PartnerRevealedEvent(declarer=state.players[1], partner=state.players[3]),
        PhaseTransitionEvent(from_phase=Phase.DEALING, to_phase=Phase.BIDDING),
    )

    new_state = state.replace(
        hands=sorted_hands,
        partners=partners,
        partner_ace_revealed=True,
        phase=Phase.BIDDING,
        turn=state.players.index(forhand),
        bid_whist_auction=auction,
    )
    return new_state, events


# ---- BIDDING handler -----------------------------------------------------


def _handle_bidding(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, PassAction):
        return _apply_pass(state)
    if isinstance(action, BidWhistBidAction):
        return _apply_bid(state, action)
    raise IllegalAction(
        f"Expected BidWhistBid/Pass in {state.phase!r}, got {type(action).__name__}"
    )


def _apply_bid(
    state: GameState, action: BidWhistBidAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    a = state.bid_whist_auction
    caller = state.current_player
    if action.level < 1 or action.level > 7:
        raise RulesViolation(f"bid whist level must be in 1..7; got {action.level}")

    trump_code = action.trump.code if action.trump is not None else None

    # Must strictly beat the current top bid (compare by level; NT ties broken by higher level).
    if a.top_level is not None and action.level <= a.top_level:
        raise RulesViolation(f"Bid {action.level} does not beat top level {a.top_level}")

    new_bids = (*a.bids, (caller, action.level, trump_code))
    new_auction = BidWhistAuctionState(
        bids=new_bids,
        passed=a.passed,
        current_bidder=a.current_bidder,
        top_level=action.level,
        top_trump=trump_code,
        top_bidder=caller,
    )
    action_event = ActionTakenEvent(caller, action)
    bid_event = BidWhistBidMadeEvent(player=caller, level=action.level, trump=trump_code)

    next_bidder = _next_active(state, new_auction, from_player=caller)
    if next_bidder is None:
        return _close_auction(state, new_auction, (action_event, bid_event))

    new_auction = BidWhistAuctionState(
        bids=new_auction.bids,
        passed=new_auction.passed,
        current_bidder=next_bidder,
        top_level=new_auction.top_level,
        top_trump=new_auction.top_trump,
        top_bidder=new_auction.top_bidder,
    )
    new_state = state.replace(
        bid_whist_auction=new_auction,
        turn=state.players.index(next_bidder),
        events=(*state.events, action_event, bid_event),
    )
    return new_state, (action_event, bid_event)


def _apply_pass(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    a = state.bid_whist_auction
    caller = state.current_player
    new_passed = a.passed | {caller}

    action_event = ActionTakenEvent(caller, PassAction())

    # Auction closes when everyone but the top bidder has passed, OR all four passed.
    active = [p for p in state.players if p not in new_passed]
    if a.top_level is None and len(new_passed) == len(state.players):
        # All passed with no bid — re-deal path: for simplicity, default to a
        # 1-trump-diamonds floor bid by the dealer so the hand still plays.
        # (Classic-table "all pass" would force a redeal; we skip that here.)
        assert state.dealer is not None
        fallback = BidWhistAuctionState(
            bids=((state.dealer, 1, "D"),),
            passed=a.passed,
            current_bidder=None,
            top_level=1,
            top_trump="D",
            top_bidder=state.dealer,
        )
        return _close_auction(state, fallback, (action_event,))

    new_auction = BidWhistAuctionState(
        bids=a.bids,
        passed=new_passed,
        current_bidder=a.current_bidder,
        top_level=a.top_level,
        top_trump=a.top_trump,
        top_bidder=a.top_bidder,
    )

    if a.top_level is not None and len(active) == 1 and active[0] == a.top_bidder:
        return _close_auction(state, new_auction, (action_event,))

    next_bidder = _next_active(state, new_auction, from_player=caller)
    if next_bidder is None and a.top_level is not None:
        return _close_auction(state, new_auction, (action_event,))

    assert next_bidder is not None
    new_auction = BidWhistAuctionState(
        bids=new_auction.bids,
        passed=new_auction.passed,
        current_bidder=next_bidder,
        top_level=new_auction.top_level,
        top_trump=new_auction.top_trump,
        top_bidder=new_auction.top_bidder,
    )
    new_state = state.replace(
        bid_whist_auction=new_auction,
        turn=state.players.index(next_bidder),
        events=(*state.events, action_event),
    )
    return new_state, (action_event,)


def _close_auction(
    state: GameState,
    auction: BidWhistAuctionState,
    pre_events: tuple[BaseEvent, ...],
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    assert auction.top_bidder is not None
    assert auction.top_level is not None

    trump_suit = (
        Suit.from_code(auction.top_trump) if auction.top_trump is not None else Suit.Unknown
    )

    won_event = BidWhistBidWonEvent(
        winner=auction.top_bidder, level=auction.top_level, trump=auction.top_trump
    )
    transition = PhaseTransitionEvent(from_phase=Phase.BIDDING, to_phase=Phase.PLAYING)

    new_state = state.replace(
        bid_whist_auction=auction,
        phase=Phase.PLAYING,
        trump=trump_suit,
        bid_winner=auction.top_bidder,
        turn=state.players.index(auction.top_bidder),
        events=(*state.events, *pre_events, won_event, transition),
    )
    return new_state, (*pre_events, won_event, transition)


def _next_active(
    state: GameState, auction: BidWhistAuctionState, *, from_player: Player
) -> Player | None:
    n = state.num_players
    start = state.players.index(from_player)
    for offset in range(1, n + 1):
        candidate = state.players[(start + offset) % n]
        if candidate not in auction.passed:
            return candidate
    return None


# ---- PLAYING handler -----------------------------------------------------


def _handle_playing(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, PlayAction):
        raise IllegalAction(f"Expected PlayAction in {state.phase!r}, got {type(action).__name__}")

    current = state.current_player

    new_hand = _deck_without(state.hands[current], action.card)
    new_hands = dict(state.hands)
    new_hands[current] = new_hand

    new_pile = _deck_with_card(state.pile, action.card)
    new_pile_play = (*state.pile_play, current)

    action_event = ActionTakenEvent(current, action)
    events_emitted: tuple[BaseEvent, ...] = (action_event,)

    if len(new_pile) == state.num_players:
        card_scores = _score_pile(new_pile, state.trump)
        trick_winner = _assign_trick(new_pile_play, card_scores)

        assert state.partners is not None
        team_id = state.partners.team_id(trick_winner)

        trick = new_pile.to_trick()
        trick_index = len(state.tricks)
        new_tricks = (*state.tricks, trick)
        new_trick_owner = dict(state.trick_owner)
        new_trick_owner[trick_index] = team_id

        trick_event = TrickTakenEvent(trick_winner, team_id, trick)
        events_emitted = (action_event, trick_event)
        new_turn = state.players.index(trick_winner)

        if len(new_tricks) >= 13:
            scoring_events = _compute_scoring(state, new_trick_owner)
            events_emitted = (*events_emitted, *scoring_events)
            new_state = state.replace(
                hands=new_hands,
                pile=Deck.empty_pile(),
                pile_play=(),
                tricks=new_tricks,
                trick_owner=new_trick_owner,
                turn=new_turn,
                phase=Phase.FINISHED,
                events=(*state.events, *events_emitted),
            )
            return new_state, events_emitted

        new_state = state.replace(
            hands=new_hands,
            pile=Deck.empty_pile(),
            pile_play=(),
            tricks=new_tricks,
            trick_owner=new_trick_owner,
            turn=new_turn,
            events=(*state.events, *events_emitted),
        )
    else:
        new_state = state.replace(
            hands=new_hands,
            pile=new_pile,
            pile_play=new_pile_play,
            turn=(state.turn + 1) % state.num_players,
            events=(*state.events, *events_emitted),
        )

    return new_state, events_emitted


# ---- scoring -------------------------------------------------------------


def _compute_scoring(state: GameState, trick_owner: dict[int, TeamID]) -> tuple[BaseEvent, ...]:
    """Made-bid: bidder's team each +level, opponents each -level. Set: reverse."""
    assert state.partners is not None
    assert state.bid_winner is not None

    a = state.bid_whist_auction
    assert a.top_level is not None

    declarer_team = int(state.partners.team_id(state.bid_winner))
    tricks_for_declarer_side = sum(1 for tid in trick_owner.values() if int(tid) == declarer_team)

    needed = 6 + a.top_level
    made = tricks_for_declarer_side >= needed
    delta = a.top_level

    per_player: dict[int, int] = {}
    for player in state.players:
        on_declarer_side = int(state.partners.team_id(player)) == declarer_team
        if made:
            per_player[player.id] = delta if on_declarer_side else -delta
        else:
            per_player[player.id] = -delta if on_declarer_side else delta

    score_event = ScoreEvent(per_player=per_player)
    transition = PhaseTransitionEvent(from_phase=Phase.PLAYING, to_phase=Phase.FINISHED)
    return (score_event, transition)


# ---- dispatch ------------------------------------------------------------


def _stub(phase: Phase) -> PhaseHandler:
    def handler(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
        _ = state, action
        raise NotImplementedError(f"bid whist does not use phase {phase.value!r}")

    handler.__name__ = f"_stub_{phase.value}"
    return handler


def _noop_dealing(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    _ = state, action
    raise IllegalAction("bid whist DEALING takes no actions; call Game.deal() instead")


HANDLERS: dict[Phase, PhaseHandler] = {
    Phase.DEALING: _noop_dealing,
    Phase.BIDDING: _handle_bidding,
    Phase.PLAYING: _handle_playing,
    Phase.BANKET: _stub(Phase.BANKET),
    Phase.CALLING: _stub(Phase.CALLING),
    Phase.KATTEN_EXCHANGE: _stub(Phase.KATTEN_EXCHANGE),
    Phase.VIP_FLIP: _stub(Phase.VIP_FLIP),
    Phase.HALVE_TRUMP: _stub(Phase.HALVE_TRUMP),
    Phase.MARKER_PLACEMENT: _stub(Phase.MARKER_PLACEMENT),
    Phase.SCORING: _stub(Phase.SCORING),
    Phase.FINISHED: _stub(Phase.FINISHED),
}


__all__ = ["HANDLERS", "_perform_deal"]
