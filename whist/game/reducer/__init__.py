"""Pure reducer — the only function that produces a new `GameState`.

`apply(state, action, *, rng) -> (new_state, events)` is deterministic given
a seeded RNG. Variant-specific handlers live in sibling modules; this
package dispatches to them based on `state.variant`.
"""

from __future__ import annotations

from random import Random

from ...errors import IllegalPhase
from ..actions import BaseAction
from ..events import BaseEvent
from ..phase import Phase
from ..state import GameState
from . import _bid_whist, _classic, _esmakker
from ._base import PhaseHandler, _rng_slot

_VARIANT_HANDLERS: dict[str, dict[Phase, PhaseHandler]] = {
    "esmakker": _esmakker.HANDLERS,
    "classic": _classic.HANDLERS,
    "bid_whist": _bid_whist.HANDLERS,
}


def apply(
    state: GameState,
    action: BaseAction,
    *,
    rng: Random | None = None,
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, BaseAction):
        raise TypeError(f"Not an action: {action!r}")

    table = _VARIANT_HANDLERS.get(state.variant)
    if table is None:
        raise IllegalPhase(f"Unknown variant: {state.variant!r}")

    handler = table.get(state.phase)
    if handler is None:
        raise IllegalPhase(f"Variant {state.variant!r} has no handler for phase {state.phase!r}")
    # Thread rng via a closure-style slot: handlers pull it from `_get_rng`.
    _rng_slot["rng"] = rng
    try:
        return handler(state, action)
    finally:
        _rng_slot["rng"] = None


def perform_deal(state: GameState, *, rng: Random) -> tuple[GameState, tuple[BaseEvent, ...]]:
    """Dispatch the initial deal to the variant-specific dealer."""
    if state.variant == "esmakker":
        return _esmakker._perform_deal(state, rng=rng)
    if state.variant == "classic":
        return _classic._perform_deal(state, rng=rng)
    if state.variant == "bid_whist":
        return _bid_whist._perform_deal(state, rng=rng)
    raise IllegalPhase(f"Unknown variant: {state.variant!r}")


# Backwards-compatible re-exports for callers that import the symbol names
# directly from the reducer module.
_perform_deal = _esmakker._perform_deal
_PHASE_HANDLERS: dict[Phase, PhaseHandler] = _esmakker.HANDLERS


__all__ = ["_PHASE_HANDLERS", "_perform_deal", "apply", "perform_deal"]
