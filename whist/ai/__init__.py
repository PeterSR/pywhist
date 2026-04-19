"""Gym-style environment wrappers around `Game` for RL training.

The heavy-lifting (policy networks, training loops) lives in `whist-ai` —
this package exposes only the environment surface and the seeded baseline AI.
"""

from .env import WhistEnv, WhistMatchEnv
from .observation import Observation

__all__ = ["Observation", "WhistEnv", "WhistMatchEnv"]
