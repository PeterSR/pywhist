"""Phase 8 — port of whist-score + zero-sum property tests."""

from __future__ import annotations

from whist.cards import Suit
from whist.game.actions import JernhaandDeclineAction
from whist.game.bids import BidModifier, NoloBid, NoloContract, NumberBid
from whist.game.events import ScoreEvent
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.player import create_default_players
from whist.game.ruleset import Ruleset
from whist.game.scoring import (
    ScoringContext,
    base_points,
    distribute,
    modifier_multiplier,
    score_magnitude,
)

# ---- base points ----------------------------------------------------------


def test_base_points_matches_whist_score_number_bids() -> None:
    ruleset = Ruleset.petersmakker()
    expected = {7: 5, 8: 10, 9: 20, 10: 40, 11: 80, 12: 160, 13: 320}
    for level, want in expected.items():
        bid = NumberBid(level, BidModifier.GODE)
        assert base_points(bid, ruleset) == want


def test_base_points_nolo() -> None:
    ruleset = Ruleset.petersmakker()
    assert base_points(NoloBid(NoloContract.SOL), ruleset) == 50
    assert base_points(NoloBid(NoloContract.REN_SOL), ruleset) == 100


def test_base_points_bordlaegger_uses_ruleset() -> None:
    r1 = Ruleset(bordlaegger_base_points=123)
    assert base_points(NoloBid(NoloContract.BORDLAEGGER), r1) == 123


# ---- modifier multiplier --------------------------------------------------


def test_modifier_multiplier_doubles_for_halve_vip_sans() -> None:
    for mod in (BidModifier.HALVE, BidModifier.VIP, BidModifier.SANS):
        assert modifier_multiplier(NumberBid(7, mod)) == 2
    assert modifier_multiplier(NumberBid(7, BidModifier.GODE)) == 1


# ---- score_magnitude ------------------------------------------------------


def test_gode_made_at_target_yields_base() -> None:
    # 7 gode, made exactly 7 tricks, no banket → base 5 x (0 over + 1) = 5.
    ruleset = Ruleset.petersmakker()
    ctx = ScoringContext(
        bid=NumberBid(7, BidModifier.GODE),
        trump=Suit.Club,
        vip_flip_count=0,
        banket=False,
        re_banket=False,
        tricks_target=7,
        tricks_taken_by_declarer_side=7,
        ruleset=ruleset,
    )
    assert score_magnitude(ctx) == 5


def test_gode_overtricks_added_linearly() -> None:
    # 7 gode +2 overtricks = base 5 x 3 = 15.
    ruleset = Ruleset.petersmakker()
    ctx = ScoringContext(
        bid=NumberBid(7, BidModifier.GODE),
        trump=Suit.Heart,
        vip_flip_count=0,
        banket=False,
        re_banket=False,
        tricks_target=7,
        tricks_taken_by_declarer_side=9,
        ruleset=ruleset,
    )
    assert score_magnitude(ctx) == 15


def test_broken_contract_negative() -> None:
    # 7 gode broken by 2 (5 tricks taken, target 7). base 5 x -2 x 2 = -20.
    ruleset = Ruleset.petersmakker()
    ctx = ScoringContext(
        bid=NumberBid(7, BidModifier.GODE),
        trump=Suit.Heart,
        vip_flip_count=0,
        banket=False,
        re_banket=False,
        tricks_target=7,
        tricks_taken_by_declarer_side=5,
        ruleset=ruleset,
    )
    assert score_magnitude(ctx) == -20


def test_banket_doubles_magnitude() -> None:
    ruleset = Ruleset.petersmakker()
    base_ctx = ScoringContext(
        bid=NumberBid(7, BidModifier.GODE),
        trump=Suit.Heart,
        vip_flip_count=0,
        banket=False,
        re_banket=False,
        tricks_target=7,
        tricks_taken_by_declarer_side=7,
        ruleset=ruleset,
    )
    banket_ctx = ScoringContext(
        bid=NumberBid(7, BidModifier.GODE),
        trump=Suit.Heart,
        vip_flip_count=0,
        banket=True,
        re_banket=False,
        tricks_target=7,
        tricks_taken_by_declarer_side=7,
        ruleset=ruleset,
    )
    rebanket_ctx = ScoringContext(
        bid=NumberBid(7, BidModifier.GODE),
        trump=Suit.Heart,
        vip_flip_count=0,
        banket=True,
        re_banket=True,
        tricks_target=7,
        tricks_taken_by_declarer_side=7,
        ruleset=ruleset,
    )
    assert score_magnitude(banket_ctx) == 2 * score_magnitude(base_ctx)
    assert score_magnitude(rebanket_ctx) == 4 * score_magnitude(base_ctx)


# ---- distribution is zero-sum --------------------------------------------


def test_distribution_zero_sum_normal_case() -> None:
    ruleset = Ruleset.petersmakker()
    players = create_default_players()
    deltas = distribute(
        magnitude=50,
        declarer=players[0],
        partner=players[2],
        all_active=players,
        selvmakker=False,
        ruleset=ruleset,
    )
    assert sum(deltas.values()) == 0
    # Declarer + partner get positive, opponents negative.
    assert deltas[players[0]] > 0
    assert deltas[players[2]] > 0
    assert deltas[players[1]] < 0
    assert deltas[players[3]] < 0


def test_distribution_zero_sum_selvmakker() -> None:
    ruleset = Ruleset(selvmakker_multiplier=3.0)
    players = create_default_players()
    deltas = distribute(
        magnitude=30,
        declarer=players[0],
        partner=None,
        all_active=players,
        selvmakker=True,
        ruleset=ruleset,
    )
    assert sum(deltas.values()) == 0
    assert deltas[players[0]] == 90  # 30 x 3 = 90, split / 3 per opponent = 30 each
    for i in (1, 2, 3):
        assert deltas[players[i]] == -30


def test_distribution_zero_sum_negative_magnitude() -> None:
    ruleset = Ruleset.petersmakker()
    players = create_default_players()
    deltas = distribute(
        magnitude=-40,
        declarer=players[0],
        partner=players[2],
        all_active=players,
        selvmakker=False,
        ruleset=ruleset,
    )
    assert sum(deltas.values()) == 0


# ---- full hand flows through SCORING to FINISHED ------------------------


def test_full_hand_emits_score_event_and_reaches_finished() -> None:
    game = Game(seed=777)
    game.deal()

    # Drive through auction + calling + banket skipping until PLAYING.
    safety = 300
    while game.state.phase != Phase.PLAYING and safety > 0:
        actions = game.valid_actions(game.current_player)
        if not actions:
            if game.state.jernhaand_pending:
                p = next(iter(game.state.jernhaand_pending))
                game.take_action(p, JernhaandDeclineAction(p))
            else:
                raise RuntimeError(f"stuck at {game.state.phase!r}")
            safety -= 1
            continue
        game.take_action(game.current_player, actions[0])
        safety -= 1

    # Play 13 tricks using actions[0].
    while not game.has_ended and safety > 0:
        actions = game.valid_actions(game.current_player)
        game.take_action(game.current_player, actions[0])
        safety -= 1

    # Check that ScoreEvent fired and phase reached FINISHED.
    assert any(isinstance(e, ScoreEvent) for e in game.state.events)
    assert game.state.phase == Phase.FINISHED

    # Zero-sum invariant over the emitted score deltas.
    score_events = [e for e in game.state.events if isinstance(e, ScoreEvent)]
    for e in score_events:
        assert sum(e.per_player.values()) == 0
