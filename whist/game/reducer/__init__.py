"""Pure reducer — the only function that produces a new `GameState`.

`apply(state, action, *, rng) -> (new_state, events)` is deterministic given
a seeded RNG. Variant-specific handlers live in sibling modules; this package
dispatches to them.
"""

from __future__ import annotations

from random import Random

from ...errors import IllegalPhase
from ..actions import BaseAction
from ..events import BaseEvent
from ..phase import Phase
from ..state import GameState
from . import _esmakker
from ._base import PhaseHandler, _rng_slot
from ._esmakker import _perform_deal

# Only the Esmakker variant exists today. `_classic` / `_bid_whist` land as
# sibling modules with their own HANDLERS tables and plug in here.
_PHASE_HANDLERS: dict[Phase, PhaseHandler] = _esmakker.HANDLERS


def apply(
    state: GameState,
    action: BaseAction,
    *,
    rng: Random | None = None,
) -> tuple[GameState, tuple[BaseEvent, ...]]:
    if not isinstance(action, BaseAction):
        raise TypeError(f"Not an action: {action!r}")

    handler: PhaseHandler | None = _PHASE_HANDLERS.get(state.phase)
    if handler is None:
        raise IllegalPhase(f"No reducer handler for phase {state.phase!r}")
    # Thread rng via a closure-style arg: handlers pull it from `_get_rng`.
    _rng_slot["rng"] = rng
    try:
        return handler(state, action)
    finally:
        _rng_slot["rng"] = None


__all__ = ["_PHASE_HANDLERS", "_perform_deal", "apply"]
