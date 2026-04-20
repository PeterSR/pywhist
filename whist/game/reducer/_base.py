"""Reducer primitives reused by every variant.

Holds the phase-handler protocol, the call-scoped RNG slot, and the
variant-agnostic card / trick helpers.
"""

from __future__ import annotations

from collections.abc import Callable
from random import Random

from ...cards import Card, Deck, Suit
from ..actions import BaseAction
from ..events import BaseEvent
from ..player import Player
from ..state import GameState
from ..tableround import TableRound

PhaseHandler = Callable[[GameState, BaseAction], tuple[GameState, tuple[BaseEvent, ...]]]


# The reducer is pure w.r.t. state+action, but redeals need an RNG. Threading
# it through every helper as an argument pollutes signatures. This tiny
# module-level slot is set by `apply` for the duration of a single call.
_rng_slot: dict[str, Random | None] = {"rng": None}


def _get_rng() -> Random:
    rng = _rng_slot["rng"]
    if rng is None:
        return Random()
    return rng


def _advance_dealer(state: GameState) -> Player:
    assert state.dealer is not None
    idx = state.players.index(state.dealer)
    return state.players[(idx + 1) % len(state.players)]


def _first_lead_forhand(state: GameState) -> Player:
    """Forhand = first seat clockwise from the dealer."""
    assert state.dealer is not None
    return next(iter(TableRound(state.dealer, list(state.players))))


def _deck_without(deck: Deck, card: Card) -> Deck:
    new_cards = list(deck.cards)
    new_cards.remove(card)
    return Deck(new_cards, allow_reorder=deck.allow_reorder)


def _deck_with_card(deck: Deck, card: Card) -> Deck:
    return Deck([*deck.cards, card], allow_reorder=deck.allow_reorder)


def _score_pile(pile: Deck, trump: Suit) -> list[int]:
    if len(pile) == 0:
        return []

    first_card = pile.cards[0]
    valid_trump = trump is not Suit.Unknown

    scores: list[int] = []
    for card in pile:
        value = card.rank.value
        if valid_trump and card.suit is trump:
            value += 100
        elif card.suit is not first_card.suit:
            value -= 100
        scores.append(value)

    if first_card == Card.joker:
        scores[0] += 1000

    return scores


def _assign_trick(pile_play: tuple[Player, ...], scores: list[int]) -> Player:
    _, winner = max(zip(scores, pile_play, strict=True))
    return winner


__all__ = [
    "PhaseHandler",
    "_advance_dealer",
    "_assign_trick",
    "_deck_with_card",
    "_deck_without",
    "_first_lead_forhand",
    "_get_rng",
    "_rng_slot",
    "_score_pile",
]
