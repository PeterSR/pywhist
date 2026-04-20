"""Bid whist: deal, auction, play, score."""

from __future__ import annotations

from whist.cards import Suit
from whist.game.actions import BidWhistBidAction, PassAction
from whist.game.events import (
    BidWhistBidMadeEvent,
    BidWhistBidWonEvent,
    DealEvent,
    PhaseTransitionEvent,
    ScoreEvent,
)
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.ruleset import Ruleset


def test_bid_whist_deal_transitions_to_bidding() -> None:
    game = Game(seed=0, ruleset=Ruleset.bid_whist())
    assert game.state is not None
    assert game.state.variant == "bid_whist"
    assert game.state.phase == Phase.DEALING
    game.deal()
    assert game.state.phase == Phase.BIDDING
    assert game.state.bid_whist_auction.current_bidder is not None


def test_bid_whist_deals_thirteen_to_each() -> None:
    game = Game(seed=1, ruleset=Ruleset.bid_whist())
    game.deal()
    state = game.state
    assert state is not None
    for p in state.players:
        assert len(state.hands[p].cards) == 13


def test_bid_whist_partners_are_fixed_seats() -> None:
    game = Game(seed=2, ruleset=Ruleset.bid_whist())
    game.deal()
    state = game.state
    assert state is not None
    assert state.partners is not None
    p = state.players
    assert state.partners.team_id(p[0]) == state.partners.team_id(p[2])
    assert state.partners.team_id(p[1]) == state.partners.team_id(p[3])


def test_bid_whist_valid_bids_include_pass_and_ladder() -> None:
    game = Game(seed=3, ruleset=Ruleset.bid_whist())
    game.deal()
    actions = game.valid_actions(game.current_player)
    assert any(isinstance(a, PassAction) for a in actions)
    # At least one bid per (level, trump-or-NT) with top_level=0 → 7 levels * 5 options = 35.
    bid_actions = [a for a in actions if isinstance(a, BidWhistBidAction)]
    assert len(bid_actions) == 7 * 5


def test_bid_whist_bid_closes_auction_when_three_pass() -> None:
    game = Game(seed=4, ruleset=Ruleset.bid_whist())
    game.deal()
    # Forhand bids 4♠.
    game.take_action(game.current_player, BidWhistBidAction(level=4, trump=Suit.Spade))
    # Next three all pass → auction closes.
    for _ in range(3):
        game.take_action(game.current_player, PassAction())

    state = game.state
    assert state is not None
    assert state.phase == Phase.PLAYING
    assert state.bid_whist_auction.top_level == 4
    assert state.bid_whist_auction.top_trump == "S"
    assert state.trump == Suit.Spade
    assert state.bid_winner is not None
    # Won event was emitted.
    won = [e for e in state.events if isinstance(e, BidWhistBidWonEvent)]
    assert len(won) == 1
    assert won[0].level == 4


def test_bid_whist_overcall_must_raise_level() -> None:
    game = Game(seed=5, ruleset=Ruleset.bid_whist())
    game.deal()
    game.take_action(game.current_player, BidWhistBidAction(level=4, trump=Suit.Club))
    # Enumeration should only show bids at level 5+.
    actions = game.valid_actions(game.current_player)
    bids = [a for a in actions if isinstance(a, BidWhistBidAction)]
    assert all(b.level >= 5 for b in bids)
    # And a level-4 overcall raises when attempted.
    raised = False
    try:
        game.take_action(game.current_player, BidWhistBidAction(level=4, trump=Suit.Spade))
    except Exception:
        raised = True
    assert raised


def test_bid_whist_no_trump_bid_sets_suit_unknown() -> None:
    game = Game(seed=6, ruleset=Ruleset.bid_whist())
    game.deal()
    game.take_action(game.current_player, BidWhistBidAction(level=4, trump=None))
    for _ in range(3):
        game.take_action(game.current_player, PassAction())
    state = game.state
    assert state is not None
    assert state.phase == Phase.PLAYING
    assert state.trump == Suit.Unknown
    assert state.bid_whist_auction.top_trump is None


def test_bid_whist_bid_made_event_recorded() -> None:
    game = Game(seed=7, ruleset=Ruleset.bid_whist())
    game.deal()
    game.take_action(game.current_player, BidWhistBidAction(level=5, trump=Suit.Heart))
    state = game.state
    assert state is not None
    made = [e for e in state.events if isinstance(e, BidWhistBidMadeEvent)]
    assert len(made) == 1
    assert made[0].level == 5
    assert made[0].trump == "H"


def test_bid_whist_full_hand_scores_zero_sum() -> None:
    """Auto-play: forhand opens at level 4 clubs, the rest pass, then play tricks."""
    game = Game(seed=8, ruleset=Ruleset.bid_whist())
    game.deal()
    game.take_action(game.current_player, BidWhistBidAction(level=4, trump=Suit.Club))
    for _ in range(3):
        game.take_action(game.current_player, PassAction())

    safety = 100
    while not game.has_ended and safety > 0:
        actions = game.valid_actions(game.current_player)
        if not actions:
            break
        game.take_action(game.current_player, actions[0])
        safety -= 1

    state = game.state
    assert state is not None
    assert state.phase == Phase.FINISHED
    score_events = [e for e in state.events if isinstance(e, ScoreEvent)]
    assert score_events
    deltas = score_events[-1].per_player
    assert sum(deltas.values()) == 0


def test_bid_whist_made_vs_set_scoring_symmetry() -> None:
    """Made: declarer side +level, opponents -level. Set: reverse. Both zero-sum."""
    for seed in range(15):
        game = Game(seed=seed, ruleset=Ruleset.bid_whist())
        game.deal()
        game.take_action(game.current_player, BidWhistBidAction(level=4, trump=Suit.Spade))
        for _ in range(3):
            game.take_action(game.current_player, PassAction())

        safety = 100
        while not game.has_ended and safety > 0:
            actions = game.valid_actions(game.current_player)
            if not actions:
                break
            game.take_action(game.current_player, actions[0])
            safety -= 1

        state = game.state
        assert state is not None
        assert state.phase == Phase.FINISHED
        score_events = [e for e in state.events if isinstance(e, ScoreEvent)]
        deltas = score_events[-1].per_player
        assert sum(deltas.values()) == 0
        # Every delta is ±4 (the bid level).
        for v in deltas.values():
            assert abs(v) == 4


def test_bid_whist_deal_emits_standard_events() -> None:
    game = Game(seed=9, ruleset=Ruleset.bid_whist())
    game.deal()
    state = game.state
    assert state is not None
    assert any(isinstance(e, DealEvent) for e in state.events)
    transitions = [
        e
        for e in state.events
        if isinstance(e, PhaseTransitionEvent) and e.to_phase == Phase.BIDDING
    ]
    assert len(transitions) == 1
