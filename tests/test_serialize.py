"""Roundtrip property tests for the msgspec serialization layer.

Every domain envelope type has `to_dict(obj) → dict → from_dict(cls, d) == obj`
exercised either by hypothesis (cards, decks, actions) or by a few pinned
fixture cases (events, state), since events/state nest many sub-types and
fuzzing the full shape is diminishing-returns.
"""

from __future__ import annotations

import msgspec
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from whist.cards import Card, Deck, Rank, Suit, suits
from whist.game.actions import (
    BaseAction,
    BidWhistBidAction,
    CallAction,
    PlayAction,
    action_from_dict,
)
from whist.game.bids import Call
from whist.game.events import ActionTakenEvent, TrickTakenEvent, event_from_dict
from whist.game.game import Game
from whist.game.partners import Partners, TeamID
from whist.game.player import Player, create_default_players
from whist.game.ruleset import Ruleset
from whist.game.state import GameState, GameStateView
from whist.serialize import (
    action_from_json,
    event_from_json,
    state_from_json,
    to_json,
)

# ---- strategies ----

_real_ranks = [r for r in Rank if r not in (Rank.Unknown,)]
_real_suits = list(suits)

cards_st = st.one_of(
    st.just(Card.joker),
    st.builds(Card, st.sampled_from(_real_suits), st.sampled_from(_real_ranks)),
)


@st.composite
def decks_st(draw: st.DrawFn) -> Deck:
    cards = draw(st.lists(cards_st, max_size=20))
    return Deck(cards)


@st.composite
def players_st(draw: st.DrawFn) -> Player:
    pid = draw(st.integers(min_value=0, max_value=100))
    name = draw(st.text(min_size=1, max_size=10))
    return Player(id=pid, name=name)


# ---- card roundtrip ----


@given(cards_st)
def test_card_roundtrip(card: Card) -> None:
    assert Card.from_dict(card.to_dict()) == card


def test_card_joker_shape() -> None:
    assert Card.joker.to_dict() == {"s": "_", "r": "*"}


def test_card_unknown_shape() -> None:
    assert Card.unknown.to_dict() == {"s": "_", "r": "_"}


# ---- deck roundtrip ----


@given(decks_st())
def test_deck_roundtrip(deck: Deck) -> None:
    assert Deck.from_list(deck.to_list()).cards == deck.cards


# ---- player / partners ----


@given(players_st())
def test_player_roundtrip(player: Player) -> None:
    assert Player.from_dict(player.to_dict()) == player


def test_partners_roundtrip_default() -> None:
    players = create_default_players()
    partners = Partners(players)
    partners.bisect(players[0], players[2])

    reconstructed = Partners.from_dict(players, partners.to_dict())
    assert reconstructed.team_id_assignment == partners.team_id_assignment
    assert [p.id for p in reconstructed.players] == [p.id for p in partners.players]


def test_partners_roundtrip_joined_pair() -> None:
    players = create_default_players()
    partners = Partners(players)
    partners.join(players[1], players[3])

    reconstructed = Partners.from_dict(players, partners.to_dict())
    assert reconstructed.team_id(players[1]) == reconstructed.team_id(players[3])
    assert reconstructed.num_teams == partners.num_teams


# ---- action roundtrip (tagged union) ----


@given(cards_st)
def test_play_action_roundtrip(card: Card) -> None:
    action = PlayAction(card)
    roundtripped = action_from_dict(action.to_dict())
    assert roundtripped == action


@given(st.sampled_from(_real_suits), st.sampled_from(_real_suits))
def test_call_action_roundtrip(trump: Suit, partner_ace: Suit) -> None:
    action = CallAction(Call(trump=trump, partner_ace=partner_ace))
    roundtripped = action_from_dict(action.to_dict())
    assert isinstance(roundtripped, CallAction)
    assert roundtripped.call.trump == trump
    assert roundtripped.call.partner_ace == partner_ace


def test_action_json_roundtrip() -> None:
    action: BaseAction = PlayAction(Card(Suit.Heart, Rank.King))
    encoded = to_json(action)
    decoded = action_from_json(encoded)
    assert decoded == action


def test_action_json_rejects_unknown_tag() -> None:
    with pytest.raises(msgspec.ValidationError):
        action_from_json(b'{"type": "nope", "card": {"s": "C", "r": "A"}}')


# ---- event roundtrip ----


def test_action_taken_event_roundtrip() -> None:
    player = Player(0, "north")
    event = ActionTakenEvent(player=player, action=PlayAction(Card(Suit.Club, Rank.Seven)))
    assert ActionTakenEvent.from_dict(event.to_dict()) == event
    assert event_from_dict(event.to_dict()) == event


def test_trick_taken_event_roundtrip() -> None:
    player = Player(2, "south")
    trick = (
        Card(Suit.Heart, Rank.Four),
        Card(Suit.Heart, Rank.King),
        Card(Suit.Heart, Rank.Two),
        Card.joker,
    )
    event = TrickTakenEvent(player=player, team_id=TeamID(42), trick=trick)
    assert TrickTakenEvent.from_dict(event.to_dict()) == event


def test_trick_event_rejects_wrong_arity() -> None:
    bad = {
        "type": "trick_taken",
        "player": {"id": 0, "name": "x"},
        "team_id": 1,
        "trick": [{"s": "C", "r": "A"}],  # only 1 card
    }
    with pytest.raises(ValueError, match="4 cards"):
        TrickTakenEvent.from_dict(bad)


def test_event_json_roundtrip() -> None:
    player = Player(1, "east")
    event = ActionTakenEvent(player=player, action=PlayAction(Card(Suit.Spade, Rank.Ace)))
    encoded = to_json(event)
    decoded = event_from_json(encoded)
    assert decoded == event


# ---- state roundtrip (full, not view) ----


def _fresh_game_state() -> GameState:
    game = Game()
    game.deal()
    # Play one action so there is something non-trivial (events + turn progress).
    actions = game.valid_actions(game.current_player)
    if actions:
        game.take_action(game.current_player, actions[0])
    return game.state


def test_game_state_roundtrip_shape() -> None:
    state = _fresh_game_state()
    d = state.to_dict()
    # Required top-level keys:
    for key in (
        "phase",
        "trump",
        "partner_ace",
        "partner_ace_revealed",
        "players",
        "hands",
        "pile",
        "tricks",
        "trick_owner",
        "partners",
        "events",
        "turn",
    ):
        assert key in d, f"missing key: {key}"
    assert len(d["players"]) == 4
    assert set(d["hands"].keys()) == {str(p["id"]) for p in d["players"]}


def test_game_state_roundtrip_values() -> None:
    state = _fresh_game_state()
    d = state.to_dict()
    rebuilt = GameState.from_dict(d)

    assert rebuilt.phase == state.phase
    assert rebuilt.trump == state.trump
    assert rebuilt.partner_ace == state.partner_ace
    assert [p.id for p in rebuilt.players] == [p.id for p in state.players]
    assert rebuilt.turn == state.turn
    for p in state.players:
        assert rebuilt.hands[p].cards == state.hands[p].cards
    assert len(rebuilt.events) == len(state.events)


def test_game_state_json_roundtrip() -> None:
    state = _fresh_game_state()
    encoded = to_json(state)
    rebuilt = state_from_json(encoded)
    assert rebuilt.phase == state.phase
    assert rebuilt.turn == state.turn


# ---- view serialize (not a roundtrip, but must be complete) ----


def test_game_state_view_serialize_shape() -> None:
    state = _fresh_game_state()
    pov = state.players[0]
    view = GameStateView(state, pov)
    out = view.serialize()

    for key in (
        "phase",
        "trump",
        "partner_ace",
        "partner_ace_revealed",
        "dealer",
        "players",
        "turn",
        "current_player",
        "pov_player",
        "hand",
        "other_hand_sizes",
        "pile",
        "pile_play",
        "tricks",
        "trick_owner",
        "partners_revealed",
        "events",
        "event_cursor_next",
    ):
        assert key in out, f"view serialize missing {key}"

    # Redaction: pov's own hand is present; other hands appear only as sizes.
    assert len(out["hand"]) == len(state.hands[pov].cards)
    for other in state.players:
        if other == pov:
            continue
        assert out["other_hand_sizes"][str(other.id)] == len(state.hands[other].cards)

    # Partners hidden until partner_ace_revealed
    if not state.partner_ace_revealed:
        assert out["partners_revealed"] == []


def test_variant_field_roundtrips_in_state_to_dict() -> None:
    """state.variant survives to_dict / from_dict for all three values."""
    for ruleset in (Ruleset.default(), Ruleset.classic(), Ruleset.bid_whist()):
        game = Game(seed=10, ruleset=ruleset)
        game.deal()
        d = game.state.to_dict()
        assert d["variant"] == ruleset.variant
        rebuilt = GameState.from_dict(d)
        assert rebuilt.variant == ruleset.variant


def test_bid_whist_auction_roundtrips() -> None:
    """BidWhistAuctionState with a populated top bid survives to_dict/from_dict."""
    game = Game(seed=11, ruleset=Ruleset.bid_whist())
    game.deal()
    # Place one bid so the auction state is non-trivial.
    game.take_action(game.current_player, BidWhistBidAction(level=4, trump=Suit.Spade))

    d = game.state.to_dict()
    rebuilt = GameState.from_dict(d)
    assert rebuilt.bid_whist_auction.top_level == 4
    assert rebuilt.bid_whist_auction.top_trump == "S"
    assert rebuilt.bid_whist_auction.top_bidder is not None
    assert len(rebuilt.bid_whist_auction.bids) == 1


def test_game_state_view_event_cursor() -> None:
    state = _fresh_game_state()
    pov = state.players[0]
    view = GameStateView(state, pov)
    out_full = view.serialize()
    cursor = out_full["event_cursor_next"]
    out_incremental = view.serialize(event_cursor=cursor)
    assert out_incremental["events"] == []
    assert out_incremental["event_cursor_next"] == cursor


# ---- settings ----

settings.register_profile("ci", max_examples=50, deadline=None)
settings.load_profile("ci")
