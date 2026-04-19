"""Pure reducer — the only function that produces a new `GameState`.

`apply(state, action, *, rng) -> (new_state, events)` is deterministic given a
seeded RNG. `Game.take_action` is a thin ergonomic wrapper over `apply`.

Dispatch is phase-first: each `Phase` value has a handler in
`_PHASE_HANDLERS`. Phases without real logic yet raise `NotImplementedError`
with a "phase X pending (lands in phase N)" message — this makes the phase
machine visible (and testable) before the feature logic lands.

Events emitted during an `apply` call are both returned and appended to
`new_state.events`, so the state alone is sufficient for replay.
"""

from __future__ import annotations

from collections.abc import Callable
from random import Random

from ..cards import Card, Deck, Rank, Suit
from ..errors import IllegalAction, IllegalPhase
from .actions import BaseAction, CallAction, PlayAction
from .events import ActionTakenEvent, BaseEvent, PhaseTransitionEvent, TrickTakenEvent
from .partners import Partners
from .phase import Phase
from .player import Player
from .state import GameState

PhaseHandler = Callable[[GameState, BaseAction], tuple[GameState, tuple[BaseEvent, ...]]]


def apply(
    state: GameState,
    action: BaseAction,
    *,
    rng: Random | None = None,
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    _ = rng  # phase 6+ uses rng for redeals
    if not isinstance(action, BaseAction):
        raise TypeError(f"Not an action: {action!r}")

    handler = _PHASE_HANDLERS.get(state.phase)
    if handler is None:
        raise IllegalPhase(f"No reducer handler for phase {state.phase!r}")
    return handler(state, action)


# ---- real handlers --------------------------------------------------------


def _handle_calling(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, CallAction):
        raise IllegalAction(f"Expected CallAction in {state.phase!r}, got {type(action).__name__}")
    return _apply_call(state, action)


def _handle_playing(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, PlayAction):
        raise IllegalAction(f"Expected PlayAction in {state.phase!r}, got {type(action).__name__}")
    return _apply_play(state, action)


def _apply_call(state: GameState, action: CallAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    caller = state.current_player
    trump = action.call.trump
    partner_ace = action.call.partner_ace

    partner_player = _find_partner_ace_player(state, partner_ace)

    assert state.partners is not None
    if partner_player is None:
        # Selvmakker / partner-ace in kitty — phase 7 handles this cleanly.
        new_partners: Partners = state.partners
    else:
        new_partners = state.partners.bisected(caller, partner_player)

    action_event = ActionTakenEvent(caller, action)
    transition = PhaseTransitionEvent(from_phase=state.phase, to_phase=Phase.PLAYING)
    events: tuple[BaseEvent, ...] = (action_event, transition)

    new_state = state.replace(
        trump=trump,
        partner_ace=partner_ace,
        partners=new_partners,
        phase=Phase.PLAYING,
        events=(*state.events, *events),
    )
    return new_state, events


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
        # Trick complete.
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


# ---- stub handlers (feature logic lands in later phases) ------------------


def _stub_for_phase(phase: Phase, pending_in: str) -> PhaseHandler:
    def handler(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
        _ = state, action
        raise NotImplementedError(f"phase {phase.value!r} pending (lands in {pending_in})")

    handler.__name__ = f"_stub_{phase.value}"
    return handler


_PHASE_HANDLERS: dict[Phase, PhaseHandler] = {
    Phase.CALLING: _handle_calling,
    Phase.PLAYING: _handle_playing,
    # Stubs — filled in by later phases. Each raises NotImplementedError if an
    # action reaches it before the feature lands.
    Phase.DEALING: _stub_for_phase(Phase.DEALING, "phase 6 (auction)"),
    Phase.BIDDING: _stub_for_phase(Phase.BIDDING, "phase 6 (auction)"),
    Phase.BANKET: _stub_for_phase(Phase.BANKET, "phase 6 (auction)"),
    Phase.KATTEN_EXCHANGE: _stub_for_phase(Phase.KATTEN_EXCHANGE, "phase 7 (katten)"),
    Phase.VIP_FLIP: _stub_for_phase(Phase.VIP_FLIP, "phase 7 (vip-flip)"),
    Phase.HALVE_TRUMP: _stub_for_phase(Phase.HALVE_TRUMP, "phase 7 (halve)"),
    Phase.MARKER_PLACEMENT: _stub_for_phase(Phase.MARKER_PLACEMENT, "phase 7 (marker)"),
    Phase.SCORING: _stub_for_phase(Phase.SCORING, "phase 8 (scoring port)"),
    Phase.FINISHED: _stub_for_phase(Phase.FINISHED, "phase 8 (scoring port)"),
}


# ---- helpers --------------------------------------------------------------


def _deck_without(deck: Deck, card: Card) -> Deck:
    new_cards = list(deck.cards)
    new_cards.remove(card)
    return Deck(new_cards, allow_reorder=deck.allow_reorder)


def _deck_with_card(deck: Deck, card: Card) -> Deck:
    return Deck([*deck.cards, card], allow_reorder=deck.allow_reorder)


def _find_partner_ace_player(state: GameState, partner_ace_suit: Suit) -> Player | None:
    """Return the player holding the partner-ace, or None if none hold it.

    A `None` return means the ace is in the kitty / discarded — the selvmakker
    variants. Phase 7 handles that branch correctly; for now the caller's
    partners assignment is left untouched (matches pre-refactor behavior).
    """
    partner_ace_card = Card(partner_ace_suit, Rank.Ace)
    for player in state.players:
        if partner_ace_card in state.hands[player]:
            return player
    return None


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


__all__ = ["apply"]
