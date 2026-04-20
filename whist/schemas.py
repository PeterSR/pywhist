"""msgspec tagged-union schemas for the wire protocol.

These `msgspec.Struct` types mirror the shape produced by each domain type's
`to_dict()`. They exist so:

- The wire format is statically documented.
- JSON decoding validates structure at the boundary before we convert to
  domain types.

Domain types (`@dataclass(frozen=True)` in `whist.game`) stay plain Python; no
msgspec import in `whist/cards/*`, `whist/game/*`. msgspec lives here and in
`whist/serialize.py` only.

State roundtrips go via plain dicts (see `GameState.serialize` /
`GameState.from_dict`).
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


class PhaseTransitionEventSchema(msgspec.Struct, tag="phase_transition", tag_field="type"):
    from_phase: str
    to_phase: str


EventSchema = ActionTakenEventSchema | TrickTakenEventSchema | PhaseTransitionEventSchema


class RulesetSchema(msgspec.Struct):
    minimum_bid: int
    bid_modifiers: list[str]
    modifier_order: list[str]
    nolo_ladder: list[str]
    klor_legal_in_almindelig: bool
    katten_exchange_mode: str
    vip_exchange_mandatory: bool
    halve_exchanger: str
    first_lead: str
    partner_ace_same_suit_as_trump: bool
    marker_card_threshold: int
    marker_card_can_trump: bool
    selvmakker_multiplier: float
    banket_enabled: bool
    banket_window_tricks: int | None
    nolo_gaa_med_settlement: str
    vip_clubs_sans_bonus: bool
    bordlaegger_base_points: int
    ren_bordlaegger_base_points: int


class SessionConfigSchema(msgspec.Struct):
    end_mode: str
    fixed_hands_count: int | None
    target_points: int | None
    time_limit_seconds: float | None
    sit_out_rotation: str


__all__ = [
    "ActionSchema",
    "ActionTakenEventSchema",
    "CallActionSchema",
    "CallSchema",
    "CardSchema",
    "EventSchema",
    "PhaseTransitionEventSchema",
    "PlayActionSchema",
    "PlayerSchema",
    "RulesetSchema",
    "SessionConfigSchema",
    "TrickTakenEventSchema",
]
