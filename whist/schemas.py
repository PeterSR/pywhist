"""msgspec tagged-union schemas for the wire protocol.

These `msgspec.Struct` types mirror the shape produced by each domain type's
`to_dict()`. They exist so:

- The wire format is statically documented.
- JSON decoding validates structure at the boundary before we convert to
  domain types.

Domain types (`@dataclass(frozen=True)` in `whist.game`) stay plain Python; no
msgspec import in `whist/cards/*`, `whist/game/*`. msgspec lives here and in
`whist/serialize.py` only.

A full `GameStateSchema` arrives with phase 4 once `GameState` is frozen and
stable. For now, state roundtrips go via plain dicts (see
`GameState.serialize` / `GameState.from_dict`).
"""

from __future__ import annotations

import msgspec


class CardSchema(msgspec.Struct):
    s: str  # suit code: C/D/H/S/_
    r: str  # rank code: A, 2-9, T, J, Q, K, *, _


class CallSchema(msgspec.Struct):
    trump: str
    partner_ace: str


class PlayerSchema(msgspec.Struct):
    id: int
    name: str


class PlayActionSchema(msgspec.Struct, tag="play", tag_field="type"):
    card: CardSchema


class CallActionSchema(msgspec.Struct, tag="call", tag_field="type"):
    call: CallSchema


ActionSchema = PlayActionSchema | CallActionSchema


class ActionTakenEventSchema(msgspec.Struct, tag="action_taken", tag_field="type"):
    player: PlayerSchema
    action: ActionSchema


class TrickTakenEventSchema(msgspec.Struct, tag="trick_taken", tag_field="type"):
    player: PlayerSchema
    team_id: int
    trick: list[CardSchema]


EventSchema = ActionTakenEventSchema | TrickTakenEventSchema


__all__ = [
    "ActionSchema",
    "ActionTakenEventSchema",
    "CallActionSchema",
    "CallSchema",
    "CardSchema",
    "EventSchema",
    "PlayActionSchema",
    "PlayerSchema",
    "TrickTakenEventSchema",
]
