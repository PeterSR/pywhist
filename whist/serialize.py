"""Top-level JSON serialization facade.

Thin wrappers over `msgspec` that delegate the actual shape-conversion to
each domain type's `to_dict` / `from_dict` classmethod. Domain types never
import msgspec; this module is the single import point for JSON I/O.

Two kinds of helpers:

- `to_dict` / `from_dict` — dict roundtrip (no JSON bytes involved).
- `to_json` / `*_from_json` — JSON roundtrip. For tagged unions (actions,
  events) we validate the bytes against the schemas in `whist.schemas`
  before handing off to the domain dispatcher.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import msgspec

from .game.actions import BaseAction, action_from_dict
from .game.events import BaseEvent, event_from_dict
from .game.state import GameState
from .schemas import ActionSchema, EventSchema

_json_encoder = msgspec.json.Encoder()
_action_schema_decoder = msgspec.json.Decoder(ActionSchema)
_event_schema_decoder = msgspec.json.Decoder(EventSchema)


def to_dict(obj: Any) -> Any:
    """Convert any domain object that exposes `to_dict()` to a plain dict."""
    return obj.to_dict()


def from_dict[T](cls: type[T], d: Mapping[str, Any]) -> T:
    """Dispatch to `cls.from_dict(d)` for types that declare one."""
    if cls is BaseAction:
        return action_from_dict(d)  # type: ignore[return-value]
    if cls is BaseEvent:
        return event_from_dict(d)  # type: ignore[return-value]
    return cls.from_dict(d)  # type: ignore[attr-defined,no-any-return]


def to_json(obj: Any) -> bytes:
    """Encode any domain object to JSON bytes via its `to_dict()` output."""
    return _json_encoder.encode(obj.to_dict())


def action_from_json(data: bytes | str) -> BaseAction:
    """Decode JSON into a domain action, validating via `ActionSchema`."""
    # Decoding via the schema validates shape and discriminator tags up front;
    # we then rebuild the domain type from the same dict shape.
    _action_schema_decoder.decode(data)
    d = msgspec.json.decode(data)
    return action_from_dict(d)


def event_from_json(data: bytes | str) -> BaseEvent:
    """Decode JSON into a domain event, validating via `EventSchema`."""
    _event_schema_decoder.decode(data)
    d = msgspec.json.decode(data)
    return event_from_dict(d)


def state_from_json(data: bytes | str) -> GameState:
    """Decode a full (non-redacted) game state from JSON.

    No msgspec schema yet — `GameStateSchema` lands with phase 4.
    """
    d = msgspec.json.decode(data)
    return GameState.from_dict(d)


__all__ = [
    "action_from_json",
    "event_from_json",
    "from_dict",
    "state_from_json",
    "to_dict",
    "to_json",
]
