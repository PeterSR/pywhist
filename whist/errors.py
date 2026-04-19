"""Exception hierarchy for pywhist.

Five base classes, intentionally small. Resist the urge to add one per rule
violation — reach for `RulesViolation` with a specific message first.
"""


class WhistError(Exception):
    """Base class for all pywhist exceptions."""


class IllegalAction(WhistError):
    """An action is not legal in the current game state.

    Covers wrong-player, wrong-phase (when the action type itself is correct
    for the phase), card-not-in-hand, and similar. For plays that violate a
    *rule* (following-suit, forced partner-ace, etc.) raise `RulesViolation`
    instead.
    """


class IllegalPhase(WhistError):
    """An operation was attempted in a phase that does not support it.

    E.g. calling `valid_actions` on a `scoring` phase or a `BidAction` during
    `playing`.
    """


class RulesViolation(WhistError):
    """A rule of the game was violated.

    Raised when an action is well-formed but violates the Esmakker rules (e.g.
    must-follow-suit, forced-play of the partner ace, partner-ace cannot share
    the trump suit outside Vip).
    """


class VariantMismatch(WhistError):
    """The active variant does not permit the requested action.

    Raised when a feature is disabled via the `Ruleset` config — e.g.
    attempting to `BanketAction` when `banket_enabled = False`.
    """


__all__ = [
    "IllegalAction",
    "IllegalPhase",
    "RulesViolation",
    "VariantMismatch",
    "WhistError",
]
