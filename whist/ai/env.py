"""Gym-style environment: `reset`, `step`, `legal_actions`.

One hand per episode by default (`WhistEnv`); a full match is a separate
wrapper (`WhistMatchEnv`). Multi-agent: the environment yields the current
player's observation on each step; `whist-ai` is responsible for turn-taking
between seats (the env does not hide information on its own beyond the
`GameStateView` redaction).
"""

from __future__ import annotations

from typing import Any

from ..game.actions import BaseAction, JernhaandDeclineAction
from ..game.events import ScoreEvent
from ..game.game import Game
from ..game.phase import Phase
from ..game.state import GameStateView
from .observation import Observation


class WhistEnv:
    """One-hand episodes.

    Agents are indexed 0..3 matching `game.state.players`. `reset(seed)`
    deals a fresh hand and returns the first agent's observation plus the
    initial `legal_actions` tuple.
    """

    def __init__(self) -> None:
        self.game: Game | None = None
        self._last_score_deltas: dict[int, int] = {}

    def reset(self, seed: int) -> Observation:
        self.game = Game(seed=seed)
        self.game.deal()
        self._last_score_deltas = {}
        # Auto-decline jernhaand so the env always lands in an actionable phase.
        assert self.game.state is not None
        while self.game.state.phase == Phase.DEALING and self.game.state.jernhaand_pending:
            p = next(iter(self.game.state.jernhaand_pending))
            self.game.take_action(p, JernhaandDeclineAction(p))
        return self._current_observation(done=False, reward=0.0)

    def step(self, action: BaseAction) -> Observation:
        assert self.game is not None
        assert self.game.state is not None
        self.game.take_action(self.game.current_player, action)
        done = self.game.state.phase == Phase.FINISHED or self.game.has_ended
        reward = 0.0
        if done:
            # Reward = per-player delta from the latest ScoreEvent.
            score_events = [e for e in self.game.state.events if isinstance(e, ScoreEvent)]
            if score_events:
                self._last_score_deltas = dict(score_events[-1].per_player)
                reward = float(self._last_score_deltas.get(self.game.current_player.id, 0))
        return self._current_observation(done=done, reward=reward)

    def legal_actions(self) -> tuple[BaseAction, ...]:
        assert self.game is not None
        return tuple(self.game.valid_actions(self.game.current_player))

    # ---- helpers ----

    def _current_observation(self, *, done: bool, reward: float) -> Observation:
        assert self.game is not None
        assert self.game.state is not None
        view = GameStateView(self.game.state, self.game.current_player)
        legal = self.legal_actions()
        # IDs = enumerate(legal). `whist-ai` is free to remap; the env only
        # guarantees that `step(legal[i])` is safe.
        legal_ids = tuple(range(len(legal)))
        return Observation(
            view_json=view.serialize(),
            legal_action_ids=legal_ids,
            reward=reward,
            done=done,
            info={"score_deltas": dict(self._last_score_deltas)} if done else None,
        )


class WhistMatchEnv:
    """Full-match episodes.

    Wraps `WhistEnv` and keeps the scoreboard running; `reset(seed)` starts a
    fresh match; `done` fires when the configured session-end mode triggers.
    Phase 12 scope is the plumbing — training-loop ergonomics (action
    masking, reward normalization) live in whist-ai.
    """

    def __init__(self, *, fixed_hands: int = 10) -> None:
        self.fixed_hands = fixed_hands
        self.env = WhistEnv()
        self.hands_played = 0
        self.totals: dict[int, int] = {}

    def reset(self, seed: int) -> Observation:
        self.hands_played = 0
        self.totals = {}
        return self.env.reset(seed)

    def step(self, action: BaseAction) -> Observation:
        obs = self.env.step(action)
        if obs.done:
            info = obs.info or {}
            for pid, delta in (info.get("score_deltas") or {}).items():
                self.totals[pid] = self.totals.get(pid, 0) + int(delta)
            self.hands_played += 1
            if self.hands_played >= self.fixed_hands:
                return obs  # match over — caller decides to stop
            # Start next hand and return *that* observation.
            next_seed = self.hands_played  # any deterministic rotation
            return self.env.reset(next_seed)
        return obs

    def legal_actions(self) -> tuple[BaseAction, ...]:
        return self.env.legal_actions()


__all__ = ["Observation", "WhistEnv", "WhistMatchEnv"]


# Pin the Any for mypy without breaking the re-exports.
_ = Any
