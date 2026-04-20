"""Esmakker (call-ace) Whist phase handlers.

The Esmakker-specific reducer logic: auction, banket, calling, katten /
vip-flip / halve-trump / marker sub-phases, and the play + scoring flow.
"""

from __future__ import annotations

from random import Random
from typing import Any

from ...cards import Card, Deck, Rank, Suit
from ...errors import IllegalAction, RulesViolation
from ..actions import (
    BanketAction,
    BanketSkipAction,
    BaseAction,
    BidAction,
    CallAction,
    DetKanJegSelvAction,
    GaaMedAction,
    HalveTrumpChoiceAction,
    JernhaandAction,
    JernhaandDeclineAction,
    KattenDiscardAction,
    KattenExchangeSkipAction,
    KattenExchangeTakeAction,
    KingCallAction,
    MarkerCardAction,
    MarkerSkipAction,
    PassAction,
    PlayAction,
    ReBanketAction,
    VipFlipAction,
    VipStopAction,
)
from ..bids import (
    BidModifier,
    NoloBid,
    NoloContract,
    NumberBid,
    bid_rank,
    rewrite_klor_almindelig,
)
from ..events import (
    ActionTakenEvent,
    AuctionBounceEvent,
    AuctionMoveEvent,
    BanketEvent,
    BaseEvent,
    BidWonEvent,
    CapsizeEvent,
    DealEvent,
    HalveTrumpChosenEvent,
    JernhaandDeclaredEvent,
    JernhaandOptionEvent,
    KattenExchangedEvent,
    KingCalledEvent,
    MarkerPlacedEvent,
    PartnerRevealedEvent,
    PhaseTransitionEvent,
    ReBanketEvent,
    RedealEvent,
    ScoreEvent,
    TrickTakenEvent,
    VipFlipEvent,
    VipStoppedEvent,
)
from ..partners import Partners
from ..phase import Phase
from ..player import Player
from ..ruleset import Ruleset
from ..scoring import ScoringContext, distribute, is_selvmakker, score_magnitude
from ..state import AuctionState, BanketState, GameState, KattenState
from ..tableround import TableRound
from ._base import (
    PhaseHandler,
    _advance_dealer,
    _assign_trick,
    _deck_with_card,
    _deck_without,
    _first_lead_forhand,
    _get_rng,
    _score_pile,
)

# ---- DEALING handler -----------------------------------------------------


def _handle_dealing(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, JernhaandAction):
        return _apply_jernhaand(state, action)
    if isinstance(action, JernhaandDeclineAction):
        return _apply_jernhaand_decline(state, action)
    raise IllegalAction(f"Only Jernhaand{{,Decline}}Action allowed in {state.phase!r}")


def _apply_jernhaand(
    state: GameState, action: JernhaandAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if action.player not in state.jernhaand_pending:
        raise RulesViolation(f"{action.player.name} is not jernhaand-eligible")

    assert state.dealer is not None
    new_dealer = _advance_dealer(state)

    action_event = ActionTakenEvent(action.player, action)
    declared_event = JernhaandDeclaredEvent(action.player)
    redeal_event = RedealEvent(reason="jernhaand", new_dealer=new_dealer)

    new_state, deal_events = _perform_deal(
        _blank_hand_state(state, new_dealer_player=new_dealer), rng=_get_rng()
    )

    events: tuple[BaseEvent, ...] = (
        action_event,
        declared_event,
        redeal_event,
        *deal_events,
    )
    return new_state.replace(events=(*state.events, *events)), events


def _apply_jernhaand_decline(
    state: GameState, action: JernhaandDeclineAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if action.player not in state.jernhaand_pending:
        raise RulesViolation(f"{action.player.name} is not jernhaand-eligible")

    new_pending = state.jernhaand_pending - {action.player}
    action_event = ActionTakenEvent(action.player, action)

    if new_pending:
        new_state = state.replace(
            jernhaand_pending=new_pending,
            events=(*state.events, action_event),
        )
        return new_state, (action_event,)

    # All declined — proceed to BIDDING.
    transition = PhaseTransitionEvent(from_phase=Phase.DEALING, to_phase=Phase.BIDDING)
    auction = _fresh_auction(state)
    new_state = state.replace(
        jernhaand_pending=frozenset(),
        phase=Phase.BIDDING,
        auction=auction,
        turn=state.players.index(auction.current_bidder) if auction.current_bidder else 0,
        events=(*state.events, action_event, transition),
    )
    return new_state, (action_event, transition)


# ---- BIDDING handler -----------------------------------------------------


def _handle_bidding(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, BidAction):
        return _apply_bid(state, action)
    if isinstance(action, PassAction):
        return _apply_pass(state)
    if isinstance(action, DetKanJegSelvAction):
        return _apply_det_kan_jeg_selv(state)
    if isinstance(action, GaaMedAction):
        return _apply_gaa_med(state)
    raise IllegalAction(
        f"Expected Bid/Pass/DetKanJegSelv/GaaMed in {state.phase!r}, got {type(action).__name__}"
    )


def _apply_bid(state: GameState, action: BidAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    bid = rewrite_klor_almindelig(action.bid, action.trump)

    # Must strictly beat top_bid.
    a = state.auction
    if a.top_bid is not None and bid_rank(bid) <= bid_rank(a.top_bid):
        raise RulesViolation(f"Bid {bid!r} does not beat top bid {a.top_bid!r}")

    caller = state.current_player
    action_event = ActionTakenEvent(caller, action)
    auction_event = AuctionMoveEvent(player=caller, kind="bid", bid=bid)

    new_bids = (*a.bids, (caller, bid))
    new_auction = AuctionState(
        bids=new_bids,
        passed=a.passed,
        current_bidder=a.current_bidder,
        top_bid=bid,
        top_bidder=caller,
        gaa_med=a.gaa_med,
    )

    # Tilbage: bounce to the most-recent non-passed previous bidder (if any).
    bounce_to = _previous_non_passed_bidder(new_auction, caller)
    events: list[BaseEvent] = [action_event, auction_event]
    new_current: Player | None
    if bounce_to is not None:
        bounce_event = AuctionBounceEvent(from_player=caller, to_player=bounce_to)
        events.append(bounce_event)
        new_current = bounce_to
    else:
        new_current = _next_active_forward(state, new_auction, from_player=caller)

    new_auction = AuctionState(
        bids=new_auction.bids,
        passed=new_auction.passed,
        current_bidder=new_current,
        top_bid=new_auction.top_bid,
        top_bidder=new_auction.top_bidder,
        gaa_med=new_auction.gaa_med,
    )

    new_state = state.replace(
        auction=new_auction,
        turn=state.players.index(new_current) if new_current is not None else state.turn,
        events=(*state.events, *events),
    )
    return new_state, tuple(events)


def _apply_pass(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    a = state.auction

    new_passed = a.passed | {caller}
    action_event = ActionTakenEvent(caller, PassAction())
    auction_event = AuctionMoveEvent(player=caller, kind="pass", bid=None)
    events: list[BaseEvent] = [action_event, auction_event]

    # Auction close conditions:
    # - All 4 players passed (no one bid) → redeal.
    # - Only one non-passed player remains (the winner).
    active = [p for p in state.players if p not in new_passed]

    if a.top_bid is None and len(active) == 0:
        # Shouldn't happen — last active just passed without bidding → same as all-pass.
        return _redeal_all_pass(state, events)

    if a.top_bid is None and all(p in new_passed for p in state.players):
        # All 4 passed with no bid → redeal.
        return _redeal_all_pass(state, events)

    if a.top_bid is not None and len(active) == 1 and active[0] == a.top_bidder:
        # Auction won.
        return _close_auction(state, new_passed, events)

    # Advance to next active forward player.
    new_auction = AuctionState(
        bids=a.bids,
        passed=new_passed,
        current_bidder=a.current_bidder,
        top_bid=a.top_bid,
        top_bidder=a.top_bidder,
        gaa_med=a.gaa_med,
    )
    new_current = _next_active_forward(state, new_auction, from_player=caller)
    if new_current is None and a.top_bid is not None:
        # Edge: only top_bidder left.
        assert a.top_bidder is not None
        return _close_auction(state, new_passed, events)

    new_auction = AuctionState(
        bids=new_auction.bids,
        passed=new_auction.passed,
        current_bidder=new_current,
        top_bid=new_auction.top_bid,
        top_bidder=new_auction.top_bidder,
        gaa_med=new_auction.gaa_med,
    )
    new_state = state.replace(
        auction=new_auction,
        turn=state.players.index(new_current) if new_current is not None else state.turn,
        events=(*state.events, *events),
    )
    return new_state, tuple(events)


def _apply_det_kan_jeg_selv(
    state: GameState,
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    """Claim the overcaller's bid. Legal only when in tilbage — i.e. you bid
    earlier and somebody just overcalled you.
    """
    a = state.auction
    caller = state.current_player

    if a.top_bid is None:
        raise RulesViolation("Cannot 'det kan jeg selv' without a top bid to claim")
    if a.top_bidder == caller:
        raise RulesViolation("Cannot 'det kan jeg selv' your own bid")
    if not any(p == caller for p, _ in a.bids):
        raise RulesViolation("Cannot 'det kan jeg selv' without a prior bid")

    previous_overcaller = a.top_bidder
    claimed_bid = a.top_bid

    action_event = ActionTakenEvent(caller, DetKanJegSelvAction())
    auction_event = AuctionMoveEvent(player=caller, kind="det_kan_jeg_selv", bid=claimed_bid)
    bounce_event = (
        AuctionBounceEvent(from_player=caller, to_player=previous_overcaller)
        if previous_overcaller is not None
        else None
    )

    new_bids = (*a.bids, (caller, claimed_bid))
    new_auction = AuctionState(
        bids=new_bids,
        passed=a.passed,
        current_bidder=previous_overcaller,
        top_bid=claimed_bid,
        top_bidder=caller,
        gaa_med=a.gaa_med,
    )

    events: list[BaseEvent] = [action_event, auction_event]
    if bounce_event is not None:
        events.append(bounce_event)

    new_state = state.replace(
        auction=new_auction,
        turn=(
            state.players.index(previous_overcaller)
            if previous_overcaller is not None
            else state.turn
        ),
        events=(*state.events, *events),
    )
    return new_state, tuple(events)


def _apply_gaa_med(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    a = state.auction
    caller = state.current_player

    if a.top_bid is None:
        raise RulesViolation("Cannot gå med without a top bid")

    is_vip = isinstance(a.top_bid, NumberBid) and a.top_bid.modifier == BidModifier.VIP
    is_nolo = isinstance(a.top_bid, NoloBid)
    if not (is_vip or is_nolo):
        raise RulesViolation(f"gå med only legal for Vip or nolo; top={a.top_bid!r}")

    action_event = ActionTakenEvent(caller, GaaMedAction())
    auction_event = AuctionMoveEvent(player=caller, kind="gaa_med", bid=None)

    # Going along forfeits overcalling — add to passed so they don't re-enter.
    new_passed = a.passed | {caller}
    new_gaa_med = (*a.gaa_med, caller)

    new_auction = AuctionState(
        bids=a.bids,
        passed=new_passed,
        current_bidder=a.current_bidder,
        top_bid=a.top_bid,
        top_bidder=a.top_bidder,
        gaa_med=new_gaa_med,
    )
    new_current = _next_active_forward(state, new_auction, from_player=caller)

    if new_current is None:
        return _close_auction(state, new_passed, [action_event, auction_event])

    new_auction = AuctionState(
        bids=new_auction.bids,
        passed=new_auction.passed,
        current_bidder=new_current,
        top_bid=new_auction.top_bid,
        top_bidder=new_auction.top_bidder,
        gaa_med=new_auction.gaa_med,
    )
    new_state = state.replace(
        auction=new_auction,
        turn=state.players.index(new_current),
        events=(*state.events, action_event, auction_event),
    )
    return new_state, (action_event, auction_event)


def _close_auction(
    state: GameState, new_passed: frozenset[Player], pre_events: list[BaseEvent]
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    a = state.auction
    assert a.top_bidder is not None
    assert a.top_bid is not None

    bid_won = BidWonEvent(winner=a.top_bidder, bid=a.top_bid)
    transition = PhaseTransitionEvent(from_phase=Phase.BIDDING, to_phase=Phase.CALLING)

    # Check for all-4-aces in declarer's hand → king_call_required
    king_call_required = _all_four_aces(state, a.top_bidder)

    new_auction = AuctionState(
        bids=a.bids,
        passed=new_passed,
        current_bidder=None,
        top_bid=a.top_bid,
        top_bidder=a.top_bidder,
        gaa_med=a.gaa_med,
    )
    new_state = state.replace(
        auction=new_auction,
        phase=Phase.CALLING,
        bid_winner=a.top_bidder,
        turn=state.players.index(a.top_bidder),
        king_call_required=king_call_required,
        events=(*state.events, *pre_events, bid_won, transition),
    )
    return new_state, (*pre_events, bid_won, transition)


def _redeal_all_pass(
    state: GameState, pre_events: list[BaseEvent]
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    new_dealer = _advance_dealer(state)
    redeal_event = RedealEvent(reason="all_pass", new_dealer=new_dealer)
    new_state, deal_events = _perform_deal(
        _blank_hand_state(state, new_dealer_player=new_dealer), rng=_get_rng()
    )

    events: tuple[BaseEvent, ...] = (*pre_events, redeal_event, *deal_events)
    new_state = new_state.replace(events=(*state.events, *events))
    return new_state, events


# ---- CALLING handler -----------------------------------------------------


def _handle_calling(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if state.king_call_required and isinstance(action, KingCallAction):
        return _apply_king_call(state, action)
    if state.king_call_required and isinstance(action, CallAction):
        raise RulesViolation("Declarer holds all 4 aces — must use KingCallAction")
    if isinstance(action, CallAction):
        return _apply_call(state, action)
    raise IllegalAction(
        f"Expected Call{'/KingCall' if state.king_call_required else ''}Action in {state.phase!r}"
    )


def _apply_call(state: GameState, action: CallAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    trump = action.call.trump
    partner_ace = action.call.partner_ace

    if trump == partner_ace and not _ruleset_allows_same_trump_partner(state):
        raise RulesViolation("Partner-ace may not be the same suit as trump")

    partner_player = _find_partner_ace_player(state, partner_ace)

    assert state.partners is not None
    if partner_player is None:
        new_partners: Partners = state.partners
    else:
        new_partners = state.partners.bisected(caller, partner_player)

    action_event = ActionTakenEvent(caller, action)
    transition = PhaseTransitionEvent(from_phase=Phase.CALLING, to_phase=Phase.BANKET)

    new_state = state.replace(
        trump=trump,
        partner_ace=partner_ace,
        partners=new_partners,
        phase=Phase.BANKET,
        events=(*state.events, action_event, transition),
    )
    return new_state, (action_event, transition)


def _apply_king_call(
    state: GameState, action: KingCallAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    trump = action.trump
    king_suit = action.king_suit

    if king_suit == trump:
        raise RulesViolation("King-suit may not be the same as trump")

    action_event = ActionTakenEvent(caller, action)
    king_event = KingCalledEvent(declarer=caller, trump=trump.code, king_suit=king_suit.code)
    transition = PhaseTransitionEvent(from_phase=Phase.CALLING, to_phase=Phase.BANKET)

    # For scoring / partnership we still need a "partner-ace"-like field.
    # Represent the king-partner via partner_ace set to king_suit; the play
    # logic uses the king (not ace) for forced-play detection here.
    new_state = state.replace(
        trump=trump,
        partner_ace=king_suit,
        phase=Phase.BANKET,
        events=(*state.events, action_event, king_event, transition),
    )
    return new_state, (action_event, king_event, transition)


# ---- BANKET handler ------------------------------------------------------


def _handle_banket(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, BanketAction):
        return _apply_banket(state, action)
    if isinstance(action, ReBanketAction):
        return _apply_re_banket(state, action)
    if isinstance(action, BanketSkipAction):
        return _apply_banket_skip(state)
    raise IllegalAction(f"Expected Banket/ReBanket/BanketSkipAction in {state.phase!r}")


def _apply_banket(
    state: GameState, action: BanketAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    declarer = state.bid_winner
    assert declarer is not None

    # Only opponents may banket.
    assert state.partners is not None
    if state.partners.team_id(caller) == state.partners.team_id(declarer):
        raise RulesViolation("Banket must come from an opponent of the declarer side")

    if state.banket.banket_by is not None:
        raise RulesViolation("Banket already declared for this contract")

    action_event = ActionTakenEvent(caller, action)
    banket_event = BanketEvent(player=caller)

    new_banket = BanketState(
        banket_by=caller,
        re_banket_by=state.banket.re_banket_by,
        declined=state.banket.declined,
    )
    # Declarer (or partner) may now re-banket — give turn to the declarer.
    new_state = state.replace(
        banket=new_banket,
        turn=state.players.index(declarer),
        events=(*state.events, action_event, banket_event),
    )
    return new_state, (action_event, banket_event)


def _apply_re_banket(
    state: GameState, action: ReBanketAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    declarer = state.bid_winner
    assert declarer is not None
    assert state.partners is not None

    if state.banket.banket_by is None:
        raise RulesViolation("Cannot re-banket without a prior banket")
    if state.banket.re_banket_by is not None:
        raise RulesViolation("Re-banket already declared")
    if state.partners.team_id(caller) != state.partners.team_id(declarer):
        raise RulesViolation("Re-banket must come from the declarer side")

    action_event = ActionTakenEvent(caller, action)
    rb_event = ReBanketEvent(player=caller)

    new_banket = BanketState(
        banket_by=state.banket.banket_by,
        re_banket_by=caller,
        declined=state.banket.declined,
    )
    new_state, transition_events = _banket_to_playing(state.replace(banket=new_banket))
    events: tuple[BaseEvent, ...] = (action_event, rb_event, *transition_events)
    return new_state.replace(events=(*state.events, *events)), events


def _apply_banket_skip(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    action_event = ActionTakenEvent(caller, BanketSkipAction())

    new_declined = state.banket.declined | {caller}
    new_banket = BanketState(
        banket_by=state.banket.banket_by,
        re_banket_by=state.banket.re_banket_by,
        declined=new_declined,
    )
    state_after = state.replace(banket=new_banket)

    # If all non-declarer-side opponents have declined banket OR the banket
    # has already landed (so we're waiting for a re-banket skip), we advance.
    declarer = state.bid_winner
    assert declarer is not None
    assert state.partners is not None
    declarer_team = state.partners.team_id(declarer)

    opponents = tuple(p for p in state.players if state.partners.team_id(p) != declarer_team)
    all_opponents_decided = all(p in new_declined or new_banket.banket_by == p for p in opponents)

    if all_opponents_decided or new_banket.banket_by is not None:
        declarer_side_skipped_rebanket = (
            new_banket.banket_by is not None
            and new_banket.re_banket_by is None
            and (caller == declarer or state.partners.team_id(caller) == declarer_team)
        )
        if declarer_side_skipped_rebanket:
            new_state, transition_events = _banket_to_playing(state_after)
            events: tuple[BaseEvent, ...] = (action_event, *transition_events)
            return new_state.replace(events=(*state.events, *events)), events
        if all_opponents_decided and new_banket.banket_by is None:
            new_state, transition_events = _banket_to_playing(state_after)
            events = (action_event, *transition_events)
            return new_state.replace(events=(*state.events, *events)), events

    # Otherwise rotate to next opponent who hasn't decided.
    next_player = _next_banket_deciding_player(state_after)
    if next_player is None:
        new_state, transition_events = _banket_to_playing(state_after)
        events = (action_event, *transition_events)
        return new_state.replace(events=(*state.events, *events)), events

    new_state = state_after.replace(
        turn=state.players.index(next_player),
        events=(*state.events, action_event),
    )
    return new_state, (action_event,)


def _banket_to_playing(
    state: GameState,
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    """Close BANKET and transition to PLAYING. First lead = declarer per
    `first_lead=declarer` or forhand per default."""
    declarer = state.bid_winner
    assert declarer is not None
    first_lead = _first_lead_forhand(state)
    transition = PhaseTransitionEvent(from_phase=Phase.BANKET, to_phase=Phase.PLAYING)
    new_state = state.replace(
        phase=Phase.PLAYING,
        turn=state.players.index(first_lead),
    )
    return new_state, (transition,)


def _next_banket_deciding_player(state: GameState) -> Player | None:
    declarer = state.bid_winner
    assert declarer is not None
    assert state.partners is not None
    declarer_team = state.partners.team_id(declarer)
    decided = state.banket.declined
    if state.banket.banket_by is not None:
        decided = decided | {state.banket.banket_by}

    for p in state.players:
        if state.partners.team_id(p) != declarer_team and p not in decided:
            return p
    return None


# ---- PLAYING handler -----------------------------------------------------


def _handle_playing(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, PlayAction):
        raise IllegalAction(f"Expected PlayAction in {state.phase!r}, got {type(action).__name__}")
    return _apply_play(state, action)


def _apply_play(state: GameState, action: PlayAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    current_player = state.current_player

    new_hand = _deck_without(state.hands[current_player], action.card)
    new_hands = dict(state.hands)
    new_hands[current_player] = new_hand

    new_pile = _deck_with_card(state.pile, action.card)
    new_pile_play = (*state.pile_play, current_player)

    partner_ace_card = Card(state.partner_ace, Rank.Ace)
    new_revealed = state.partner_ace_revealed or (action.card == partner_ace_card)

    action_event = ActionTakenEvent(current_player, action)
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

        # Last trick? Transition to SCORING → FINISHED inline.
        if len(new_tricks) >= 13:
            scoring_events = _compute_scoring(state, new_trick_owner, new_tricks)
            events_emitted = (*events_emitted, *scoring_events)
            new_state = state.replace(
                hands=new_hands,
                pile=Deck.empty_pile(),
                pile_play=(),
                tricks=new_tricks,
                trick_owner=new_trick_owner,
                partner_ace_revealed=new_revealed,
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
            partner_ace_revealed=new_revealed,
            turn=new_turn,
            events=(*state.events, *events_emitted),
        )
    else:
        new_state = state.replace(
            hands=new_hands,
            pile=new_pile,
            pile_play=new_pile_play,
            partner_ace_revealed=new_revealed,
            turn=(state.turn + 1) % state.num_players,
            events=(*state.events, *events_emitted),
        )

    return new_state, events_emitted


# ---- stubs for non-implemented phases ------------------------------------


def _stub_for_phase(phase: Phase, reason: str) -> PhaseHandler:
    def handler(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
        _ = state, action
        raise NotImplementedError(f"phase {phase.value!r} not implemented: {reason}")

    handler.__name__ = f"_stub_{phase.value}"
    return handler


def _handle_katten_exchange(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, KattenExchangeSkipAction):
        return _katten_skip(state)
    if isinstance(action, KattenExchangeTakeAction):
        return _katten_take(state)
    if isinstance(action, KattenDiscardAction):
        return _katten_discard(state, action)
    raise IllegalAction(f"Expected katten action in {state.phase!r}")


def _katten_skip(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    exchanger = state.current_player
    action_event = ActionTakenEvent(exchanger, KattenExchangeSkipAction())
    exchanged_event = KattenExchangedEvent(exchanger, took_count=0, discards_count=0)
    transition = PhaseTransitionEvent(from_phase=Phase.KATTEN_EXCHANGE, to_phase=Phase.PLAYING)
    new_state = state.replace(
        phase=Phase.PLAYING,
        events=(*state.events, action_event, exchanged_event, transition),
    )
    return new_state, (action_event, exchanged_event, transition)


def _katten_take(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    exchanger = state.current_player
    katten = state.katten
    if not katten.cards:
        raise RulesViolation("Katten is empty — nothing to take")

    new_hand_cards = [*state.hands[exchanger].cards, *katten.cards]
    new_hands = dict(state.hands)
    new_hands[exchanger] = Deck(new_hand_cards)
    # Holder is set; we're now waiting for KattenDiscardAction.
    new_katten = KattenState(cards=katten.cards, flipped=katten.flipped, holder=exchanger)
    action_event = ActionTakenEvent(exchanger, KattenExchangeTakeAction())
    new_state = state.replace(
        hands=new_hands, katten=new_katten, events=(*state.events, action_event)
    )
    return new_state, (action_event,)


def _katten_discard(
    state: GameState, action: KattenDiscardAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if state.katten.holder is None:
        raise RulesViolation("No active katten holder — issue KattenExchangeTake first")
    exchanger = state.katten.holder
    if state.current_player != exchanger:
        raise RulesViolation("Only the katten holder may discard")

    hand = state.hands[exchanger]
    for c in action.cards:
        if c not in hand.cards:
            raise RulesViolation(f"Card not in hand: {c!r}")

    new_hand_cards = list(hand.cards)
    for c in action.cards:
        new_hand_cards.remove(c)
    new_hands = dict(state.hands)
    new_hands[exchanger] = Deck(new_hand_cards)

    new_discarded = (*state.discarded, *action.cards)
    action_event = ActionTakenEvent(exchanger, action)
    exchanged_event = KattenExchangedEvent(exchanger, took_count=3, discards_count=3)
    transition = PhaseTransitionEvent(from_phase=Phase.KATTEN_EXCHANGE, to_phase=Phase.PLAYING)
    new_state = state.replace(
        hands=new_hands,
        discarded=new_discarded,
        katten=KattenState(),  # clear
        phase=Phase.PLAYING,
        events=(*state.events, action_event, exchanged_event, transition),
    )
    return new_state, (action_event, exchanged_event, transition)


def _handle_halve_trump(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, HalveTrumpChoiceAction):
        raise IllegalAction(f"Expected HalveTrumpChoiceAction in {state.phase!r}")
    partner = state.current_player
    action_event = ActionTakenEvent(partner, action)
    chosen_event = HalveTrumpChosenEvent(partner=partner, trump=action.trump.code)
    transition = PhaseTransitionEvent(from_phase=Phase.HALVE_TRUMP, to_phase=Phase.BANKET)
    new_state = state.replace(
        trump=action.trump,
        phase=Phase.BANKET,
        events=(*state.events, action_event, chosen_event, transition),
    )
    return new_state, (action_event, chosen_event, transition)


def _handle_vip_flip(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, VipFlipAction):
        return _vip_flip_next(state)
    if isinstance(action, VipStopAction):
        return _vip_stop(state)
    raise IllegalAction(f"Expected Vip{{Flip,Stop}}Action in {state.phase!r}")


def _vip_flip_next(
    state: GameState,
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    katten = state.katten
    idx = sum(1 for f in katten.flipped if f)
    if idx >= len(katten.cards):
        raise RulesViolation("No more katten cards to flip")
    card = katten.cards[idx]
    new_flipped = tuple(True if i == idx else f for i, f in enumerate(katten.flipped))
    new_katten = KattenState(cards=katten.cards, flipped=new_flipped, holder=katten.holder)
    action_event = ActionTakenEvent(state.current_player, VipFlipAction())
    flip_event = VipFlipEvent(index=idx, card=card)
    new_state = state.replace(katten=new_katten, events=(*state.events, action_event, flip_event))
    return new_state, (action_event, flip_event)


def _vip_stop(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    katten = state.katten
    # Trump = suit of the most-recently flipped card, or sans if it's a joker.
    idx = sum(1 for f in katten.flipped if f) - 1
    if idx < 0:
        raise RulesViolation("Cannot stop before any flip")
    revealed = katten.cards[idx]
    # Joker revealed = sans (no trump); otherwise suit of the revealed card.
    final_trump = Suit.Unknown if revealed == Card.joker else revealed.suit

    action_event = ActionTakenEvent(state.current_player, VipStopAction())
    stop_event = VipStoppedEvent(final_trump=final_trump.code, flip_count=idx + 1)
    transition = PhaseTransitionEvent(from_phase=Phase.VIP_FLIP, to_phase=Phase.KATTEN_EXCHANGE)
    new_state = state.replace(
        trump=final_trump,
        phase=Phase.KATTEN_EXCHANGE,
        events=(*state.events, action_event, stop_event, transition),
    )
    return new_state, (action_event, stop_event, transition)


def _handle_marker_placement(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if isinstance(action, MarkerSkipAction):
        return _marker_skip(state)
    if isinstance(action, MarkerCardAction):
        return _marker_place(state, action)
    raise IllegalAction(f"Expected Marker{{Card,Skip}}Action in {state.phase!r}")


def _marker_skip(state: GameState) -> tuple[GameState, tuple[BaseEvent, ...]]:
    action_event = ActionTakenEvent(state.current_player, MarkerSkipAction())
    transition = PhaseTransitionEvent(from_phase=Phase.MARKER_PLACEMENT, to_phase=Phase.PLAYING)
    new_state = state.replace(phase=Phase.PLAYING, events=(*state.events, action_event, transition))
    return new_state, (action_event, transition)


def _marker_place(
    state: GameState, action: MarkerCardAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    declarer = state.bid_winner
    if caller != declarer:
        raise RulesViolation("Only the declarer may place the marker card")

    # Threshold: declarer must hold ≤ threshold cards of the partner-ace suit.
    # The threshold comes from `Ruleset.marker_card_threshold`. The reducer
    # currently lacks a ruleset reference here, so we use the default of 1.
    marker_threshold = 1
    declarer_hand = state.hands[declarer]
    count_in_suit = sum(1 for c in declarer_hand.cards if c.suit == state.partner_ace)
    if count_in_suit > marker_threshold:
        raise RulesViolation(
            f"Marker requires ≤{marker_threshold} of partner-ace suit; "
            f"declarer holds {count_in_suit}"
        )
    if action.card not in declarer_hand.cards:
        raise RulesViolation("Marker card must come from declarer's hand")

    new_hand_cards = [c for c in declarer_hand.cards if c != action.card]
    new_hands = dict(state.hands)
    new_hands[declarer] = Deck(new_hand_cards)

    action_event = ActionTakenEvent(declarer, action)
    placed_event = MarkerPlacedEvent(player=declarer, claimed_suit=state.partner_ace.code)
    # Marker placement reveals the partnership.
    partner_reveal: tuple[BaseEvent, ...] = ()
    assert state.partners is not None
    partner_player = _find_partner_ace_player(state, state.partner_ace)
    if partner_player is not None:
        partner_reveal = (PartnerRevealedEvent(declarer=declarer, partner=partner_player),)

    transition = PhaseTransitionEvent(from_phase=Phase.MARKER_PLACEMENT, to_phase=Phase.PLAYING)
    new_state = state.replace(
        hands=new_hands,
        marker_card=action.card,
        partner_ace_revealed=True,
        phase=Phase.PLAYING,
        events=(
            *state.events,
            action_event,
            placed_event,
            *partner_reveal,
            transition,
        ),
    )
    return new_state, (action_event, placed_event, *partner_reveal, transition)


def _compute_scoring(
    pre_trick_state: GameState,
    trick_owner: dict[int, Any],  # TeamID → int-equivalent
    tricks: tuple[Any, ...],
) -> tuple[BaseEvent, ...]:
    """Compute the hand's score events at trick 13.

    `pre_trick_state` is the state before the final trick collection.
    `trick_owner` is the fully-populated owner map; `tricks` the full list.
    """
    assert pre_trick_state.partners is not None
    assert pre_trick_state.bid_winner is not None

    declarer = pre_trick_state.bid_winner
    partners_obj = pre_trick_state.partners
    declarer_team = partners_obj.team_id(declarer)

    # Count tricks taken by declarer's team.
    declarer_side_tricks = sum(1 for _tidx, owner in trick_owner.items() if owner == declarer_team)

    # Pull the winning bid from the auction state.
    auction = pre_trick_state.auction
    if auction.top_bid is None:
        # Auction never produced a bid (shouldn't happen post-BIDDING), skip.
        return ()
    bid = auction.top_bid

    # tricks_target: from the bid (number = level, nolo = 0 for Ren-variants).
    if isinstance(bid, NumberBid):
        tricks_target = bid.level
    else:
        ren_contracts = (NoloContract.REN_SOL, NoloContract.REN_BORDLAEGGER)
        tricks_target = 0 if bid.contract in ren_contracts else 1

    # Selvmakker?
    selvmakker = is_selvmakker(partners_obj, declarer)
    partner: Player | None = None
    if not selvmakker:
        team_members = partners_obj.team_members(declarer_team)
        others = [p for p in team_members if p != declarer]
        partner = others[0] if others else None

    # Ruleset fallback — the reducer doesn't yet see Game.ruleset here.
    ruleset = Ruleset.default()

    # vip_flip_count: tracked only for Vip bids; a baseline of 1 is assumed.
    vip_flip_count = 1 if isinstance(bid, NumberBid) and bid.modifier.value == "vip" else 0

    ctx = ScoringContext(
        bid=bid,
        trump=pre_trick_state.trump,
        vip_flip_count=vip_flip_count,
        banket=pre_trick_state.banket.banket_by is not None,
        re_banket=pre_trick_state.banket.re_banket_by is not None,
        tricks_target=tricks_target,
        tricks_taken_by_declarer_side=declarer_side_tricks,
        ruleset=ruleset,
    )
    magnitude = score_magnitude(ctx)
    all_players = list(pre_trick_state.players)
    per_player = distribute(
        magnitude,
        declarer=declarer,
        partner=partner,
        all_active=all_players,
        selvmakker=selvmakker,
        ruleset=ruleset,
    )
    score_event = ScoreEvent(per_player={p.id: v for p, v in per_player.items()})
    transition = PhaseTransitionEvent(from_phase=Phase.PLAYING, to_phase=Phase.FINISHED)
    # Capsize event if nolo declarer exceeded target.
    if isinstance(bid, NoloBid) and declarer_side_tricks > tricks_target:
        return (
            CapsizeEvent(declarer=declarer, tricks_taken=declarer_side_tricks),
            score_event,
            transition,
        )
    return (score_event, transition)


# ---- deal / dealer advancement -------------------------------------------


def _perform_deal(state: GameState, *, rng: Random) -> tuple[GameState, tuple[BaseEvent, ...]]:
    """Deal 13 cards to each of 4 players; emit DealEvent + JernhaandOption if
    applicable. Transition phase to BIDDING if no jernhaand pending.
    """
    assert state.dealer is not None
    if len(state.players) != 4:
        raise IllegalAction("_perform_deal expects exactly 4 players")

    deck = Deck.full_deck()
    deck.shuffle(rng=rng)

    hand_size = 13
    tableround = TableRound(state.dealer, list(state.players))

    new_hands: dict[Player, Deck] = {}
    deck_cards = list(deck.cards)
    for p in tableround:
        cards_for_p = [deck_cards.pop() for _ in range(hand_size)]
        hand = Deck(cards_for_p)
        hand.sort()
        new_hands[p] = hand

    kitty = Deck(deck_cards)

    deal_event = DealEvent(dealer=state.dealer, seed=state.seed)

    jernhaand_eligible = frozenset(p for p in state.players if _has_jernhaand(new_hands[p]))

    events: list[BaseEvent] = [deal_event]
    if jernhaand_eligible:
        events.append(JernhaandOptionEvent(eligible=tuple(jernhaand_eligible)))
        next_phase = Phase.DEALING
        turn = 0
        auction = state.auction
    else:
        transition = PhaseTransitionEvent(from_phase=Phase.DEALING, to_phase=Phase.BIDDING)
        events.append(transition)
        next_phase = Phase.BIDDING
        forhand = next(iter(TableRound(state.dealer, list(state.players))))
        turn = state.players.index(forhand)
        auction = AuctionState(current_bidder=forhand)

    new_state = state.replace(
        hands=new_hands,
        kitty=kitty,
        phase=next_phase,
        turn=turn,
        jernhaand_pending=jernhaand_eligible,
        auction=auction,
    )
    return new_state, tuple(events)


def _blank_hand_state(state: GameState, *, new_dealer_player: Player) -> GameState:
    """Reset per-hand state for a redeal — dealer advances, hands clear."""
    return state.replace(
        dealer=new_dealer_player,
        bid_winner=None,
        hands={p: Deck.empty() for p in state.players},
        trump=Suit.Unknown,
        partner_ace=Suit.Unknown,
        partner_ace_revealed=False,
        partners=Partners(list(state.players)),
        kitty=None,
        pile=Deck.empty_pile(),
        pile_play=(),
        tricks=(),
        trick_owner={},
        phase=Phase.DEALING,
        turn=0,
        auction=AuctionState(),
        banket=BanketState(),
        jernhaand_pending=frozenset(),
        king_call_required=False,
    )


# ---- auction helpers -----------------------------------------------------


def _fresh_auction(state: GameState) -> AuctionState:
    assert state.dealer is not None
    forhand = next(iter(TableRound(state.dealer, list(state.players))))
    return AuctionState(current_bidder=forhand)


def _previous_non_passed_bidder(auction: AuctionState, exclude: Player) -> Player | None:
    """Most-recent distinct non-passed bidder (for tilbage bounce)."""
    for p, _ in reversed(auction.bids[:-1]):  # skip the bid we just made
        if p == exclude:
            continue
        if p in auction.passed:
            continue
        return p
    return None


def _next_active_forward(
    state: GameState, auction: AuctionState, from_player: Player
) -> Player | None:
    """Next clockwise player who hasn't passed. Returns None if none exist."""
    n = state.num_players
    start = state.players.index(from_player)
    for offset in range(1, n + 1):
        candidate = state.players[(start + offset) % n]
        if candidate not in auction.passed:
            return candidate
    return None


# ---- hand analysis helpers -----------------------------------------------


_FACE_AND_UP = frozenset({Rank.Jack, Rank.Queen, Rank.King, Rank.Ace, Rank.Joker})


def _has_jernhaand(hand: Deck) -> bool:
    """Jernhaand: no aces, no face cards, no jokers."""
    return all(c.rank not in _FACE_AND_UP for c in hand.cards)


def _all_four_aces(state: GameState, player: Player) -> bool:
    hand = state.hands[player]
    aces = sum(1 for c in hand.cards if c.rank == Rank.Ace)
    return aces == 4


def _ruleset_allows_same_trump_partner(state: GameState) -> bool:
    _ = state
    # Placeholder — once the ruleset is threaded into the reducer this should
    # read `state.ruleset.partner_ace_same_suit_as_trump`. Default: false.
    return False


def _find_partner_ace_player(state: GameState, partner_ace_suit: Suit) -> Player | None:
    partner_ace_card = Card(partner_ace_suit, Rank.Ace)
    for player in state.players:
        if partner_ace_card in state.hands[player]:
            return player
    return None


# ---- dispatch table ------------------------------------------------------


HANDLERS: dict[Phase, PhaseHandler] = {
    Phase.DEALING: _handle_dealing,
    Phase.BIDDING: _handle_bidding,
    Phase.BANKET: _handle_banket,
    Phase.CALLING: _handle_calling,
    Phase.PLAYING: _handle_playing,
    Phase.KATTEN_EXCHANGE: _handle_katten_exchange,
    Phase.VIP_FLIP: _handle_vip_flip,
    Phase.HALVE_TRUMP: _handle_halve_trump,
    Phase.MARKER_PLACEMENT: _handle_marker_placement,
    # SCORING and FINISHED are terminal — _handle_playing computes the score
    # inline at trick 13 and transitions straight to FINISHED.
    Phase.SCORING: _stub_for_phase(Phase.SCORING, "scored inline from PLAYING"),
    Phase.FINISHED: _stub_for_phase(Phase.FINISHED, "hand is over"),
}


__all__ = ["HANDLERS", "_perform_deal"]
