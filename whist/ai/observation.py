"""RL observation type — the payload handed to an agent at `step`.

Numpy-free: callers own feature encoding. This is the protocol surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Observation:
    """Per-agent observation.

    - `view_json`: the current player's `GameStateView.serialize()` dict.
    - `legal_action_ids`: indices into the action space exposed by the env
      (`WhistEnv.action_space`). Callers map these to feature tensors.
    - `reward`: per-step reward. For hand-episode envs, non-zero only on the
      final step (the per-player score delta from the hand's ScoreEvent).
    - `done`: True when the hand / match has ended.
    """

    view_json: dict[str, Any]
    legal_action_ids: tuple[int, ...]
    reward: float = 0.0
    done: bool = False
    info: dict[str, Any] | None = None
