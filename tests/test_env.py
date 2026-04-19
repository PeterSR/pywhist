"""Phase 12 — `WhistEnv` smoke tests.

The real training loop lives in whist-ai; these tests exercise the plumbing.
"""

from __future__ import annotations

from whist.ai.env import WhistEnv
from whist.ai.observation import Observation


def _play_episode(seed: int) -> Observation:
    env = WhistEnv()
    obs = env.reset(seed)
    safety = 500
    while not obs.done and safety > 0:
        legal = env.legal_actions()
        if not legal:
            break
        obs = env.step(legal[0])
        safety -= 1
    return obs


def test_single_episode_runs_to_done() -> None:
    obs = _play_episode(seed=0)
    assert obs.done
    # Sum of final score deltas is zero per the scoring invariant.
    info = obs.info or {}
    deltas = info.get("score_deltas") or {}
    assert sum(deltas.values()) == 0


def test_observation_exposes_view_json_and_legal_ids() -> None:
    env = WhistEnv()
    obs = env.reset(seed=1)
    assert "phase" in obs.view_json
    assert "hand" in obs.view_json
    # legal_action_ids align with env.legal_actions()
    legal = env.legal_actions()
    assert len(obs.legal_action_ids) == len(legal)


def test_hundred_episodes_clean() -> None:
    # Scaled-down version of the plan's 1000-episode smoke (fast enough for CI).
    for seed in range(100):
        obs = _play_episode(seed)
        assert obs.done
        info = obs.info or {}
        deltas = info.get("score_deltas") or {}
        assert sum(deltas.values()) == 0
