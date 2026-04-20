"""Classic partnership whist.

Four players, fixed partnerships (seats 0+2 vs seats 1+3), no bidding, trump
is chosen by the `classic_trump_source` ruleset flag (default: the last card
dealt to the dealer). The team that wins more than six tricks scores
`(tricks - 6)` per extra trick; the other team pays the same amount
(zero-sum settlement matches the rest of pywhist).
"""

from __future__ import annotations

from random import Random

from ...cards import Card, Deck
from ...errors import IllegalAction
from ..actions import BaseAction, PlayAction
from ..events import (
    ActionTakenEvent,
    BaseEvent,
    DealEvent,
    PartnerRevealedEvent,
    PhaseTransitionEvent,
    ScoreEvent,
    TrickTakenEvent,
)
from ..partners import Partners, TeamID
from ..phase import Phase
from ..player import Player
from ..state import GameState
from ..tableround import TableRound
from ._base import (
    PhaseHandler,
    _assign_trick,
    _deck_with_card,
    _deck_without,
    _score_pile,
)

# ---- deal ----------------------------------------------------------------


def _perform_deal(state: GameState, *, rng: Random) -> tuple[GameState, tuple[BaseEvent, ...]]:
    """Deal a 52-card pack one-at-a-time clockwise, starting at forhand.

    The dealer's final card (card 52) sets trump. Partnerships are fixed:
    seats 0 and 2 vs seats 1 and 3. Phase transitions directly to PLAYING.
    """
    assert state.dealer is not None
    if len(state.players) != 4:
        raise IllegalAction("classic whist deal expects exactly 4 players")

    deck = Deck.full_deck(num_jokers=0)
    deck.shuffle(rng=rng)

    # Round-robin deal, starting from forhand.
    order = list(TableRound(state.dealer, list(state.players)))
    hands: dict[Player, list[Card]] = {p: [] for p in state.players}
    for i, card in enumerate(deck.cards):
        recipient = order[i % 4]
        hands[recipient].append(card)

    sorted_hands: dict[Player, Deck] = {}
    for p, cards in hands.items():
        d = Deck(cards)
        d.sort()
        sorted_hands[p] = d

    # Trump comes from the last card dealt to the dealer.
    trump_card = hands[state.dealer][-1]
    trump = trump_card.suit

    # Fixed N-S vs E-W partnerships; seats 0+2 vs 1+3.
    partners = Partners(list(state.players))
    partners.bisect(state.players[0], state.players[2])

    forhand = order[0]
    events: tuple[BaseEvent, ...] = (
        DealEvent(dealer=state.dealer, seed=state.seed),
        PartnerRevealedEvent(declarer=state.players[0], partner=state.players[2]),
        PartnerRevealedEvent(declarer=state.players[1], partner=state.players[3]),
        PhaseTransitionEvent(from_phase=Phase.DEALING, to_phase=Phase.PLAYING),
    )

    new_state = state.replace(
        hands=sorted_hands,
        trump=trump,
        partners=partners,
        partner_ace_revealed=True,  # Classic partnerships are public.
        phase=Phase.PLAYING,
        turn=state.players.index(forhand),
    )
    return new_state, events


# ---- PLAYING handler -----------------------------------------------------


def _handle_playing(
    state: GameState, action: BaseAction
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, PlayAction):
        raise IllegalAction(f"Expected PlayAction in {state.phase!r}, got {type(action).__name__}")

    current_player = state.current_player

    new_hand = _deck_without(state.hands[current_player], action.card)
    new_hands = dict(state.hands)
    new_hands[current_player] = new_hand

    new_pile = _deck_with_card(state.pile, action.card)
    new_pile_play = (*state.pile_play, current_player)

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
    """Winning team scores (tricks - 6) per extra trick; losing team pays
    the same per-player amount. Zero-sum.
    """
    assert state.partners is not None
    tally: dict[int, int] = {}
    for team_id in trick_owner.values():
        tally[int(team_id)] = tally.get(int(team_id), 0) + 1

    winning_tid, winning_tricks = max(tally.items(), key=lambda kv: kv[1])
    margin = max(0, winning_tricks - 6)

    per_player: dict[int, int] = {}
    for player in state.players:
        player_tid = int(state.partners.team_id(player))
        per_player[player.id] = margin if player_tid == winning_tid else -margin

    score_event = ScoreEvent(per_player=per_player)
    transition = PhaseTransitionEvent(from_phase=Phase.PLAYING, to_phase=Phase.FINISHED)
    return (score_event, transition)


# ---- stubs ---------------------------------------------------------------


def _stub(phase: Phase) -> PhaseHandler:
    def handler(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
        _ = state, action
        raise NotImplementedError(f"classic whist does not use phase {phase.value!r}")

    handler.__name__ = f"_stub_{phase.value}"
    return handler


# ---- dispatch ------------------------------------------------------------


def _noop_dealing(state: GameState, action: BaseAction) -> tuple[GameState, tuple[BaseEvent, ...]]:
    """DEALING is terminal for classic — the deal was performed at Game start."""
    _ = state, action
    raise IllegalAction("classic whist DEALING takes no actions; call Game.deal() instead")


HANDLERS: dict[Phase, PhaseHandler] = {
    Phase.DEALING: _noop_dealing,
    Phase.PLAYING: _handle_playing,
    # Classic doesn't use these phases; raise if something tries to advance them.
    Phase.BIDDING: _stub(Phase.BIDDING),
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
