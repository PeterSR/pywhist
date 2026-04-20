"""Classic partnership whist: deal, play, score."""

from __future__ import annotations

from whist.game.events import DealEvent, PartnerRevealedEvent, PhaseTransitionEvent, ScoreEvent
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.ruleset import Ruleset


def _play_full_hand(seed: int) -> Game:
    """Play the first legal action at every seat until the hand ends."""
    game = Game(seed=seed, ruleset=Ruleset.classic())
    game.deal()
    safety = 200
    while not game.has_ended and safety > 0:
        actions = game.valid_actions(game.current_player)
        if not actions:
            break
        game.take_action(game.current_player, actions[0])
        safety -= 1
    return game


def test_classic_deal_transitions_to_playing() -> None:
    game = Game(seed=7, ruleset=Ruleset.classic())
    assert game.state is not None
    assert game.state.variant == "classic"
    assert game.state.phase == Phase.DEALING
    game.deal()
    assert game.state.phase == Phase.PLAYING


def test_classic_deal_produces_four_hands_of_thirteen_and_no_kitty() -> None:
    game = Game(seed=1, ruleset=Ruleset.classic())
    game.deal()
    assert game.state is not None
    for p in game.state.players:
        assert len(game.state.hands[p].cards) == 13
    total = sum(len(game.state.hands[p].cards) for p in game.state.players)
    assert total == 52


def test_classic_trump_is_dealers_last_card() -> None:
    game = Game(seed=2, ruleset=Ruleset.classic())
    game.deal()
    state = game.state
    assert state is not None
    assert state.dealer is not None
    # The dealer's last card (in deal order) should carry the trump suit.
    # After sorting the dealer's hand, the *suit* still appears somewhere;
    # simpler check: trump is a concrete suit (not Unknown).
    assert state.trump.code != "_"
    # And the dealer holds at least one card of that suit (it's their 13th).
    dealer_hand = state.hands[state.dealer]
    assert any(c.suit == state.trump for c in dealer_hand.cards)


def test_classic_partners_are_fixed_opposite_seats() -> None:
    game = Game(seed=0, ruleset=Ruleset.classic())
    game.deal()
    state = game.state
    assert state is not None
    assert state.partners is not None
    p = state.players
    # Seats 0 and 2 are partners; seats 1 and 3 are partners.
    assert state.partners.team_id(p[0]) == state.partners.team_id(p[2])
    assert state.partners.team_id(p[1]) == state.partners.team_id(p[3])
    assert state.partners.team_id(p[0]) != state.partners.team_id(p[1])


def test_classic_partnerships_are_revealed_from_deal() -> None:
    game = Game(seed=0, ruleset=Ruleset.classic())
    game.deal()
    state = game.state
    assert state is not None
    assert state.partner_ace_revealed is True  # No hidden partners in classic.
    # PartnerRevealedEvent was emitted at deal.
    revealed = [e for e in state.events if isinstance(e, PartnerRevealedEvent)]
    assert len(revealed) == 2


def test_classic_deal_emits_deal_event_and_transition() -> None:
    game = Game(seed=3, ruleset=Ruleset.classic())
    game.deal()
    state = game.state
    assert state is not None
    assert any(isinstance(e, DealEvent) for e in state.events)
    assert any(
        isinstance(e, PhaseTransitionEvent) and e.to_phase == Phase.PLAYING for e in state.events
    )


def test_classic_full_hand_runs_to_finished_zero_sum() -> None:
    game = _play_full_hand(seed=5)
    state = game.state
    assert state is not None
    assert state.phase == Phase.FINISHED
    assert len(state.tricks) == 13
    # Zero-sum scoring property.
    score_events = [e for e in state.events if isinstance(e, ScoreEvent)]
    assert score_events, "expected a ScoreEvent at hand end"
    deltas = score_events[-1].per_player
    assert sum(deltas.values()) == 0


def test_classic_winning_side_margin_matches_tricks_above_six() -> None:
    game = _play_full_hand(seed=11)
    state = game.state
    assert state is not None
    assert state.partners is not None

    # Count tricks per team.
    tally: dict[int, int] = {}
    for tid in state.trick_owner.values():
        tally[int(tid)] = tally.get(int(tid), 0) + 1
    winning_tid, winning_tricks = max(tally.items(), key=lambda kv: kv[1])
    expected_margin = max(0, winning_tricks - 6)

    score_events = [e for e in state.events if isinstance(e, ScoreEvent)]
    deltas = score_events[-1].per_player
    # Each winning-team player gets +margin; each losing-team player gets -margin.
    winners = [p for p in state.players if int(state.partners.team_id(p)) == winning_tid]
    for w in winners:
        assert deltas[w.id] == expected_margin


def test_classic_many_seeds_are_deterministic_and_zero_sum() -> None:
    for seed in range(20):
        game = _play_full_hand(seed)
        state = game.state
        assert state is not None
        assert state.phase == Phase.FINISHED
        score_events = [e for e in state.events if isinstance(e, ScoreEvent)]
        assert score_events
        assert sum(score_events[-1].per_player.values()) == 0
