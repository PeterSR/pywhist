"""Sub-phase handlers: katten, vip-flip, halve-trump, marker.

Each sub-phase handler is exercised by constructing the state directly.
"""

from __future__ import annotations

from typing import Any

import pytest

from whist.cards import Card, Deck, Rank, Suit
from whist.errors import RulesViolation
from whist.game.actions import (
    HalveTrumpChoiceAction,
    KattenDiscardAction,
    KattenExchangeSkipAction,
    KattenExchangeTakeAction,
    MarkerCardAction,
    MarkerSkipAction,
    VipFlipAction,
    VipStopAction,
)
from whist.game.events import (
    HalveTrumpChosenEvent,
    KattenExchangedEvent,
    MarkerPlacedEvent,
    PartnerRevealedEvent,
    VipFlipEvent,
    VipStoppedEvent,
)
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.reducer import apply
from whist.game.state import KattenState

# ---- katten exchange ----------------------------------------------------


def _state_in_katten_exchange(game: Game) -> None:
    """Mutate a fresh game into KATTEN_EXCHANGE with kitty-populated katten."""
    assert game.state.kitty is not None
    katten = KattenState(
        cards=tuple(game.state.kitty.cards),
        flipped=(False,) * len(game.state.kitty.cards),
    )
    game.state = game.state.replace(phase=Phase.KATTEN_EXCHANGE, katten=katten)


def test_katten_skip_advances_to_playing() -> None:
    game = Game(seed=100)
    game.deal()
    _state_in_katten_exchange(game)

    new_state, events = apply(game.state, KattenExchangeSkipAction())
    assert new_state.phase == Phase.PLAYING
    assert any(isinstance(e, KattenExchangedEvent) and e.took_count == 0 for e in events)


def test_katten_take_then_discard_three_advances() -> None:
    game = Game(seed=101)
    game.deal()
    _state_in_katten_exchange(game)

    exchanger = game.current_player

    # Take: hand grows by 3.
    after_take, _ = apply(game.state, KattenExchangeTakeAction())
    assert len(after_take.hands[exchanger].cards) == len(game.state.hands[exchanger].cards) + 3

    # Choose 3 cards to discard.
    discards = tuple(after_take.hands[exchanger].cards[-3:])
    after_discard, events = apply(
        after_take,
        KattenDiscardAction(cards=discards),  # type: ignore[arg-type]
    )
    assert after_discard.phase == Phase.PLAYING
    assert len(after_discard.hands[exchanger].cards) == len(game.state.hands[exchanger].cards)
    assert len(after_discard.discarded) == 3
    assert any(isinstance(e, KattenExchangedEvent) and e.took_count == 3 for e in events)


def test_katten_discard_wrong_count_rejected() -> None:
    # The action type enforces exactly 3 cards at construction time.
    with pytest.raises(ValueError, match="Expected 3 cards"):
        KattenDiscardAction.from_dict({"type": "katten_discard", "cards": [{"s": "C", "r": "A"}]})


def test_katten_discard_without_prior_take_rejected() -> None:
    game = Game(seed=102)
    game.deal()
    _state_in_katten_exchange(game)

    p = game.current_player
    some_cards = tuple(game.state.hands[p].cards[:3])
    with pytest.raises(RulesViolation, match="katten"):
        apply(game.state, KattenDiscardAction(cards=some_cards))  # type: ignore[arg-type]


# ---- vip flip -----------------------------------------------------------


def test_vip_flip_reveals_sequential_cards() -> None:
    game = Game(seed=103)
    game.deal()
    cards = (
        Card(Suit.Heart, Rank.Five),
        Card(Suit.Diamond, Rank.Seven),
        Card(Suit.Spade, Rank.Nine),
    )
    game.state = game.state.replace(
        phase=Phase.VIP_FLIP,
        katten=KattenState(cards=cards, flipped=(False, False, False)),
    )

    s1, events1 = apply(game.state, VipFlipAction())
    assert any(isinstance(e, VipFlipEvent) and e.index == 0 and e.card == cards[0] for e in events1)

    s2, events2 = apply(s1, VipFlipAction())
    assert any(isinstance(e, VipFlipEvent) and e.index == 1 and e.card == cards[1] for e in events2)

    s3, events3 = apply(s2, VipStopAction())
    # Stop after second flip → trump = second card's suit (diamonds).
    assert s3.trump == Suit.Diamond
    assert s3.phase == Phase.KATTEN_EXCHANGE
    assert any(isinstance(e, VipStoppedEvent) for e in events3)


def test_vip_stop_on_joker_becomes_sans() -> None:
    game = Game(seed=104)
    game.deal()
    cards = (Card.joker, Card(Suit.Diamond, Rank.Seven))
    game.state = game.state.replace(
        phase=Phase.VIP_FLIP,
        katten=KattenState(cards=cards, flipped=(False, False)),
    )
    after_flip, _ = apply(game.state, VipFlipAction())
    after_stop, events = apply(after_flip, VipStopAction())
    # Revealed = joker → sans (Suit.Unknown).
    assert after_stop.trump == Suit.Unknown
    stop_events = [e for e in events if isinstance(e, VipStoppedEvent)]
    assert stop_events
    assert stop_events[0].final_trump == "_"


# ---- halve trump --------------------------------------------------------


def test_halve_partner_picks_trump() -> None:
    game = Game(seed=105)
    game.deal()
    game.state = game.state.replace(phase=Phase.HALVE_TRUMP)

    new_state, events = apply(game.state, HalveTrumpChoiceAction(trump=Suit.Diamond))
    assert new_state.trump == Suit.Diamond
    assert new_state.phase == Phase.BANKET
    assert any(isinstance(e, HalveTrumpChosenEvent) for e in events)


# ---- marker placement ---------------------------------------------------


def _rig_declarer_hand_low(
    game: Game, declarer: Any, partner_ace_suit: Suit, count_in_suit: int
) -> None:
    # Build a deterministic 13-card hand: `count_in_suit` cards of the
    # partner-ace suit (low ranks) + fill with non-suit cards.
    suit_cards = [
        Card(partner_ace_suit, rank)
        for rank in (Rank.Two, Rank.Three, Rank.Four, Rank.Five, Rank.Six, Rank.Seven)
    ][:count_in_suit]
    filler_suits = [s for s in (Suit.Club, Suit.Diamond, Suit.Spade) if s != partner_ace_suit][:3]
    filler: list[Card] = []
    rank_cycle = [
        Rank.Two,
        Rank.Three,
        Rank.Four,
        Rank.Five,
        Rank.Six,
        Rank.Seven,
        Rank.Eight,
        Rank.Nine,
        Rank.Ten,
    ]
    for s in filler_suits:
        for r in rank_cycle:
            filler.append(Card(s, r))
            if len(filler) + count_in_suit >= 13:
                break
        if len(filler) + count_in_suit >= 13:
            break
    rigged = suit_cards + filler[: 13 - count_in_suit]
    assert len(rigged) == 13
    rigged_hands = dict(game.state.hands)
    rigged_hands[declarer] = Deck(rigged)
    game.state = game.state.replace(hands=rigged_hands)


def test_marker_skip_advances_to_playing() -> None:
    game = Game(seed=106)
    game.deal()
    game.state = game.state.replace(phase=Phase.MARKER_PLACEMENT)

    new_state, _ = apply(game.state, MarkerSkipAction())
    assert new_state.phase == Phase.PLAYING


def test_marker_place_when_threshold_satisfied() -> None:
    game = Game(seed=107)
    game.deal()
    declarer = game.state.players[0]
    partner_ace_suit = Suit.Heart
    _rig_declarer_hand_low(game, declarer, partner_ace_suit, count_in_suit=1)

    game.state = game.state.replace(
        phase=Phase.MARKER_PLACEMENT,
        bid_winner=declarer,
        partner_ace=partner_ace_suit,
        turn=game.state.players.index(declarer),
    )
    # Choose the 1 heart card from declarer's hand.
    chosen = next(c for c in game.state.hands[declarer].cards if c.suit == partner_ace_suit)
    new_state, events = apply(game.state, MarkerCardAction(card=chosen))
    assert new_state.phase == Phase.PLAYING
    assert new_state.marker_card == chosen
    assert new_state.partner_ace_revealed
    assert any(isinstance(e, MarkerPlacedEvent) for e in events)


def test_marker_place_fails_when_over_threshold() -> None:
    game = Game(seed=108)
    game.deal()
    declarer = game.state.players[0]
    partner_ace_suit = Suit.Heart
    _rig_declarer_hand_low(game, declarer, partner_ace_suit, count_in_suit=3)

    game.state = game.state.replace(
        phase=Phase.MARKER_PLACEMENT,
        bid_winner=declarer,
        partner_ace=partner_ace_suit,
        turn=game.state.players.index(declarer),
    )
    chosen = next(c for c in game.state.hands[declarer].cards if c.suit == partner_ace_suit)
    with pytest.raises(RulesViolation, match="Marker requires"):
        apply(game.state, MarkerCardAction(card=chosen))


def test_marker_place_emits_partner_revealed_when_partner_exists() -> None:
    game = Game(seed=109)
    game.deal()
    declarer = game.state.players[0]
    partner_ace_suit = Suit.Heart
    _rig_declarer_hand_low(game, declarer, partner_ace_suit, count_in_suit=1)

    # Make sure some other player holds the partner_ace card so PartnerRevealedEvent fires.
    ace_card = Card(partner_ace_suit, Rank.Ace)
    other = game.state.players[2]
    other_hand = list(game.state.hands[other].cards)
    if ace_card not in other_hand:
        # Swap in the ace.
        other_hand[0] = ace_card
    rigged_hands = dict(game.state.hands)
    rigged_hands[other] = Deck(other_hand)
    game.state = game.state.replace(
        hands=rigged_hands,
        phase=Phase.MARKER_PLACEMENT,
        bid_winner=declarer,
        partner_ace=partner_ace_suit,
        turn=game.state.players.index(declarer),
    )
    chosen = next(c for c in game.state.hands[declarer].cards if c.suit == partner_ace_suit)
    _, events = apply(game.state, MarkerCardAction(card=chosen))
    assert any(isinstance(e, PartnerRevealedEvent) for e in events)


def test_marker_place_selvmakker_own_hand_skips_partner_reveal() -> None:
    """Declarer holds the partner-ace themselves (selvmakker-via-own-hand):
    marker placement should NOT emit PartnerRevealedEvent(declarer, declarer).
    """
    game = Game(seed=110)
    game.deal()
    declarer = game.state.players[0]
    partner_ace_suit = Suit.Heart
    # Rig declarer's hand: exactly 1 heart — the Ace of Hearts.
    ace_card = Card(partner_ace_suit, Rank.Ace)
    declarer_hand = [ace_card] + [
        Card(s, r)
        for s in (Suit.Club, Suit.Diamond, Suit.Spade)
        for r in (Rank.Two, Rank.Three, Rank.Four, Rank.Five)
    ]
    rigged_hands = dict(game.state.hands)
    rigged_hands[declarer] = Deck(declarer_hand)
    game.state = game.state.replace(
        hands=rigged_hands,
        phase=Phase.MARKER_PLACEMENT,
        bid_winner=declarer,
        partner_ace=partner_ace_suit,
        turn=game.state.players.index(declarer),
    )

    _, events = apply(game.state, MarkerCardAction(card=ace_card))
    assert not any(isinstance(e, PartnerRevealedEvent) for e in events)
