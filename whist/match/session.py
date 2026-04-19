"""Session-envelope config: when a match ends, how sit-out rotates.

Separate from `Ruleset` because these are session-level decisions (how many
hands, whether we play to a target, who sits out) that live on `Match`, not on
`Game`. A single session uses one `SessionConfig` from start to finish.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

EndMode = Literal["open", "fixed_hands", "target_points", "time"]
SitOutRotation = Literal["manual", "clockwise", "longest_out"]


@dataclass(frozen=True)
class SessionConfig:
    end_mode: EndMode = "open"
    fixed_hands_count: int | None = None
    target_points: int | None = None
    time_limit_seconds: float | None = None
    sit_out_rotation: SitOutRotation = "manual"

    @classmethod
    def ai_default(cls) -> SessionConfig:
        """SessionConfig used by `WhistEnv` — fixed 100-hand sessions."""
        return cls(end_mode="fixed_hands", fixed_hands_count=100)

    def to_dict(self) -> dict[str, Any]:
        return {
            "end_mode": self.end_mode,
            "fixed_hands_count": self.fixed_hands_count,
            "target_points": self.target_points,
            "time_limit_seconds": self.time_limit_seconds,
            "sit_out_rotation": self.sit_out_rotation,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> SessionConfig:
        return cls(
            end_mode=d["end_mode"],
            fixed_hands_count=d["fixed_hands_count"],
            target_points=d["target_points"],
            time_limit_seconds=d["time_limit_seconds"],
            sit_out_rotation=d["sit_out_rotation"],
        )


__all__ = ["EndMode", "SessionConfig", "SitOutRotation"]
