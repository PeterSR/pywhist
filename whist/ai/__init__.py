"""Gym-style environment wrappers around `Game` for RL training.

Policy networks and training loops are out of scope — this package exposes
only the environment surface and the seeded baseline AI.
"""

from .env import WhistEnv, WhistMatchEnv
from .observation import Observation

__all__ = ["Observation", "WhistEnv", "WhistMatchEnv"]
