"""Auction, banket, jernhaand, all-4-aces.

Covers:
- minimum bid 7
- klør-almindelig → gode auto-rewrite
- modifier ordering within a level (BID_LADDER)
- sol beats any 9-bid; loses to any 10-bid
- tilbage bounce with det-kan-jeg-selv
- all-pass redeal + dealer advance
- banket only within window (declarer-side only may re-banket)
- jernhaand detection + declare/decline
- all-4-aces → king call with trump-king forbidden
"""

from __future__ import annotations

import pytest

from whist.cards import Card, Deck, Rank, Suit
from whist.errors import RulesViolation
from whist.game.actions import (
    BanketAction,
    BanketSkipAction,
    BidAction,
    CallAction,
    DetKanJegSelvAction,
    JernhaandAction,
    JernhaandDeclineAction,
    KingCallAction,
    PassAction,
    ReBanketAction,
)
from whist.game.bids import (
    BID_LADDER,
    BidModifier,
    Call,
    NoloBid,
    NoloContract,
    NumberBid,
    bid_rank,
    rewrite_klor_almindelig,
)
from whist.game.events import (
    AuctionBounceEvent,
    AuctionMoveEvent,
    BidWonEvent,
    DealEvent,
    JernhaandDeclaredEvent,
    KingCalledEvent,
    RedealEvent,
)
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.reducer import apply

# ---- BID_LADDER ----------------------------------------------------------


def test_bid_ladder_minimum_is_seven_almindelig() -> None:
    assert BID_LADDER[0] == NumberBid(7, BidModifier.ALMINDELIG)


def test_bid_ladder_modifier_order_within_level_seven() -> None:
    level7 = BID_LADDER[0:5]
    assert level7 == (
        NumberBid(7, BidModifier.ALMINDELIG),
        NumberBid(7, BidModifier.GODE),
        NumberBid(7, BidModifier.HALVE),
        NumberBid(7, BidModifier.VIP),
        NumberBid(7, BidModifier.SANS),
    )


def test_bid_ladder_nolo_placement() -> None:
    # Sol comes after 9-level, Ren Sol after 10-level, etc.
    sol_idx = BID_LADDER.index(NoloBid(NoloContract.SOL))
    nine_sans_idx = BID_LADDER.index(NumberBid(9, BidModifier.SANS))
    ten_alm_idx = BID_LADDER.index(NumberBid(10, BidModifier.ALMINDELIG))
    assert nine_sans_idx < sol_idx < ten_alm_idx


def test_sol_beats_any_9_bid() -> None:
    sol = NoloBid(NoloContract.SOL)
    for mod in BidModifier:
        if mod == BidModifier.ALMINDELIG:
            # klør-almindelig is the same rank as almindelig here; ladder has it.
            pass
        nine = NumberBid(9, mod)
        assert bid_rank(sol) > bid_rank(nine)


def test_sol_loses_to_any_10_bid() -> None:
    sol = NoloBid(NoloContract.SOL)
    for mod in BidModifier:
        ten = NumberBid(10, mod)
        assert bid_rank(sol) < bid_rank(ten)


# ---- klør-almindelig auto-rewrite ---------------------------------------


def test_klor_almindelig_rewrites_to_gode() -> None:
    bid = NumberBid(7, BidModifier.ALMINDELIG)
    rewritten = rewrite_klor_almindelig(bid, Suit.Club)
    assert rewritten == NumberBid(7, BidModifier.GODE)


def test_non_klor_almindelig_unchanged() -> None:
    bid = NumberBid(7, BidModifier.ALMINDELIG)
    assert rewrite_klor_almindelig(bid, Suit.Heart) == bid


def test_reducer_applies_klor_rewrite_at_bid_time() -> None:
    game = Game(seed=10)
    game.deal()
    state = game.state
    # Opening bid: almindelig with klør → gode
    action = BidAction(NumberBid(7, BidModifier.ALMINDELIG), trump=Suit.Club)
    new_state, _events = apply(state, action)
    assert new_state.auction.top_bid == NumberBid(7, BidModifier.GODE)


# ---- tilbage bounce + det-kan-jeg-selv -----------------------------------


def test_tilbage_bounce_on_overcall() -> None:
    game = Game(seed=11)
    game.deal()
    # Player A bids 7 gode.
    p_a = game.current_player
    game.take_action(p_a, BidAction(NumberBid(7, BidModifier.GODE)))
    # Next forward active.
    p_b = game.current_player
    assert p_b != p_a
    # B overcalls with 7 halve. Turn bounces back to A (previous bidder).
    _new_state, events = apply(game.state, BidAction(NumberBid(7, BidModifier.HALVE)))
    assert any(isinstance(e, AuctionBounceEvent) and e.to_player == p_a for e in events)


def test_det_kan_jeg_selv_claims_overcall() -> None:
    game = Game(seed=12)
    game.deal()
    p_a = game.current_player
    game.take_action(p_a, BidAction(NumberBid(7, BidModifier.GODE)))
    # B overcalls with 7 halve.
    p_b = game.current_player
    game.take_action(p_b, BidAction(NumberBid(7, BidModifier.HALVE)))
    # Turn bounced to A. A claims with det-kan-jeg-selv.
    assert game.current_player == p_a
    game.take_action(p_a, DetKanJegSelvAction())
    assert game.state.auction.top_bid == NumberBid(7, BidModifier.HALVE)
    assert game.state.auction.top_bidder == p_a


def test_det_kan_jeg_selv_requires_top_bid() -> None:
    # No top bid exists → det-kan-jeg-selv illegal.
    game = Game(seed=13)
    game.deal()
    with pytest.raises(RulesViolation, match="top bid"):
        apply(game.state, DetKanJegSelvAction())


def test_det_kan_jeg_selv_requires_prior_bid_from_self() -> None:
    # Top bid exists but current player hasn't bid before. Construct a state
    # where A has bid, then B is current_bidder without ever having bid.
    game = Game(seed=31)
    game.deal()
    a = game.current_player
    game.take_action(a, BidAction(NumberBid(7, BidModifier.GODE)))
    # Turn is now B (no prior bid). Force-advance the turn field to B.
    b = game.state.players[(game.state.players.index(a) + 1) % 4]
    state = game.state.replace(turn=game.state.players.index(b))
    with pytest.raises(RulesViolation, match="prior bid"):
        apply(state, DetKanJegSelvAction())


# ---- pass / all-pass redeal ----------------------------------------------


def test_all_pass_triggers_redeal_and_dealer_advance() -> None:
    game = Game(seed=14)
    game.deal()
    original_dealer = game.state.dealer
    assert original_dealer is not None

    # All 4 pass.
    emitted_redeal = False
    for _ in range(4):
        player = game.current_player
        _, events = apply(game.state, PassAction())
        if any(isinstance(e, RedealEvent) for e in events):
            emitted_redeal = True
        game.take_action(player, PassAction())
        if game.state.phase != Phase.BIDDING:
            break

    assert emitted_redeal
    # After redeal, the dealer has advanced.
    new_dealer = game.state.dealer
    assert new_dealer != original_dealer


def test_simple_auction_closes_with_forward_passes() -> None:
    game = Game(seed=15)
    game.deal()
    bidder = game.current_player
    game.take_action(bidder, BidAction(NumberBid(7, BidModifier.GODE)))
    # All remaining forward bidders pass.
    safety = 20
    while game.state.phase == Phase.BIDDING and safety > 0:
        game.take_action(game.current_player, PassAction())
        safety -= 1

    assert game.state.phase == Phase.CALLING
    assert game.state.bid_winner == bidder
    assert any(isinstance(e, BidWonEvent) for e in game.state.events)


# ---- banket --------------------------------------------------------------


def _drive_to_banket(game: Game) -> None:
    """Drive game to the BANKET phase via bid + passes + calling."""
    if game.state.phase == Phase.DEALING and game.state.jernhaand_pending:
        p = next(iter(game.state.jernhaand_pending))
        game.take_action(p, JernhaandDeclineAction(p))
    # Bid minimum + 3 passes.
    game.take_action(game.current_player, BidAction(NumberBid(7, BidModifier.GODE)))
    while game.state.phase == Phase.BIDDING:
        game.take_action(game.current_player, PassAction())
    # Now in CALLING. Issue a CallAction with non-trump partner-ace.
    game.take_action(
        game.current_player,
        CallAction(Call(trump=Suit.Heart, partner_ace=Suit.Spade)),
    )


def test_banket_from_opponent_transitions_declarer_to_turn() -> None:
    game = Game(seed=16)
    game.deal()
    _drive_to_banket(game)
    assert game.state.phase == Phase.BANKET

    # Find an opponent.
    assert game.state.bid_winner is not None
    assert game.state.partners is not None
    declarer = game.state.bid_winner
    declarer_team = game.state.partners.team_id(declarer)
    opponent = next(
        p for p in game.state.players if game.state.partners.team_id(p) != declarer_team
    )

    # Manually apply: put opponent in turn seat and banket.
    state_with_opp = game.state.replace(turn=game.state.players.index(opponent))
    new_state, _events = apply(state_with_opp, BanketAction())
    assert new_state.banket.banket_by == opponent
    # Turn should now be the declarer's (for re-banket choice).
    assert new_state.players[new_state.turn] == declarer


def test_re_banket_must_come_from_declarer_side() -> None:
    game = Game(seed=17)
    game.deal()
    _drive_to_banket(game)
    assert game.state.bid_winner is not None
    assert game.state.partners is not None
    declarer = game.state.bid_winner
    declarer_team = game.state.partners.team_id(declarer)
    opponent = next(
        p for p in game.state.players if game.state.partners.team_id(p) != declarer_team
    )

    # Opponent banks, then opponent tries to re-banket — should fail.
    state_with_opp = game.state.replace(turn=game.state.players.index(opponent))
    after_banket, _ = apply(state_with_opp, BanketAction())

    with pytest.raises(RulesViolation, match="declarer side"):
        apply(
            after_banket.replace(turn=after_banket.players.index(opponent)),
            ReBanketAction(),
        )


def test_banket_skip_by_all_opponents_advances_to_playing() -> None:
    game = Game(seed=18)
    game.deal()
    _drive_to_banket(game)
    # Each opponent skips in order.
    safety = 8
    while game.state.phase == Phase.BANKET and safety > 0:
        game.take_action(game.current_player, BanketSkipAction())
        safety -= 1
    assert game.state.phase == Phase.PLAYING


# ---- jernhaand -----------------------------------------------------------


def test_jernhaand_detection_and_decline() -> None:
    # Construct a state where player 0 has a jernhaand hand (no J/Q/K/A/joker).
    game = Game(seed=19)
    game.deal()
    player = game.state.players[0]
    low_cards = [
        Card(Suit.Heart, Rank.Two),
        Card(Suit.Heart, Rank.Three),
        Card(Suit.Heart, Rank.Four),
        Card(Suit.Diamond, Rank.Five),
        Card(Suit.Diamond, Rank.Six),
        Card(Suit.Diamond, Rank.Seven),
        Card(Suit.Club, Rank.Two),
        Card(Suit.Club, Rank.Three),
        Card(Suit.Club, Rank.Four),
        Card(Suit.Spade, Rank.Five),
        Card(Suit.Spade, Rank.Six),
        Card(Suit.Spade, Rank.Seven),
        Card(Suit.Spade, Rank.Eight),
    ]
    rigged_hands = dict(game.state.hands)
    rigged_hands[player] = Deck(low_cards)
    rigged_state = game.state.replace(
        hands=rigged_hands,
        jernhaand_pending=frozenset({player}),
        phase=Phase.DEALING,
    )

    # Decline — should advance to BIDDING.
    new_state, _events = apply(rigged_state, JernhaandDeclineAction(player))
    assert new_state.phase == Phase.BIDDING
    assert player not in new_state.jernhaand_pending


def test_jernhaand_declare_triggers_redeal() -> None:
    game = Game(seed=20)
    game.deal()
    player = game.state.players[0]
    original_dealer = game.state.dealer
    assert original_dealer is not None

    rigged_state = game.state.replace(
        jernhaand_pending=frozenset({player}),
        phase=Phase.DEALING,
    )
    new_state, events = apply(rigged_state, JernhaandAction(player))
    assert any(isinstance(e, JernhaandDeclaredEvent) for e in events)
    assert any(isinstance(e, RedealEvent) for e in events)
    # Dealer advanced.
    assert new_state.dealer != original_dealer


# ---- all-4-aces / king call ---------------------------------------------


def test_king_call_required_when_declarer_has_all_aces() -> None:
    game = Game(seed=21)
    game.deal()
    # Rig declarer's hand to have all four aces.
    declarer = game.current_player
    aces = [
        Card(Suit.Club, Rank.Ace),
        Card(Suit.Diamond, Rank.Ace),
        Card(Suit.Heart, Rank.Ace),
        Card(Suit.Spade, Rank.Ace),
    ]
    # Fill remaining 9 with random low cards from the default hand.
    extras = [c for c in game.state.hands[declarer].cards if c.rank != Rank.Ace][:9]
    rigged_hands = dict(game.state.hands)
    rigged_hands[declarer] = Deck(aces + extras)
    state = game.state.replace(hands=rigged_hands)
    game.state = state

    # Drive auction: declarer bids 7 gode, others pass.
    game.take_action(declarer, BidAction(NumberBid(7, BidModifier.GODE)))
    safety = 5
    while game.state.phase == Phase.BIDDING and safety > 0:
        game.take_action(game.current_player, PassAction())
        safety -= 1

    assert game.state.phase == Phase.CALLING
    assert game.state.king_call_required


def test_king_call_rejects_trump_king() -> None:
    # Directly dispatch a KingCallAction with matching trump and king_suit.
    game = Game(seed=22)
    game.deal()
    state = game.state.replace(phase=Phase.CALLING, king_call_required=True)
    with pytest.raises(RulesViolation, match="King-suit"):
        apply(state, KingCallAction(trump=Suit.Heart, king_suit=Suit.Heart))


def test_king_call_success_emits_king_called_event() -> None:
    game = Game(seed=23)
    game.deal()
    state = game.state.replace(phase=Phase.CALLING, king_call_required=True)
    _new_state, events = apply(state, KingCallAction(trump=Suit.Heart, king_suit=Suit.Spade))
    assert any(isinstance(e, KingCalledEvent) for e in events)


# ---- DealEvent seed recorded --------------------------------------------


def test_deal_event_records_seed() -> None:
    game = Game(seed=424242)
    game.deal()
    deal_events = [e for e in game.state.events if isinstance(e, DealEvent)]
    assert deal_events
    assert deal_events[0].seed == 424242


def test_auction_move_event_records_bid() -> None:
    game = Game(seed=99)
    game.deal()
    game.take_action(game.current_player, BidAction(NumberBid(7, BidModifier.GODE)))
    moves = [e for e in game.state.events if isinstance(e, AuctionMoveEvent)]
    assert moves
    assert moves[-1].kind == "bid"
    assert moves[-1].bid == NumberBid(7, BidModifier.GODE)
