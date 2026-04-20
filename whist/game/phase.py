"""Phase enum for the Esmakker game state machine.

`StrEnum` is used so a phase round-trips trivially as JSON and prints as its
own name. Add members conservatively — every phase is a dispatch case.
"""

from enum import StrEnum


class Phase(StrEnum):
    """Phases of a single deal (one game in the Match sense).

    The canonical ordering is:

        dealing → bidding → [banket] → [halve_trump | vip_flip]
                                     → katten_exchange
                                     → [marker_placement]
                                     → playing → scoring → finished

    Bracketed phases are conditional on the winning bid type or declarer
    choice.
    """

    DEALING = "dealing"
    BIDDING = "bidding"
    BANKET = "banket"
    HALVE_TRUMP = "halve_trump"
    VIP_FLIP = "vip_flip"
    KATTEN_EXCHANGE = "katten_exchange"
    MARKER_PLACEMENT = "marker_placement"
    PLAYING = "playing"
    SCORING = "scoring"
    FINISHED = "finished"

    # Legacy combined trump+partner-ace selection phase, dispatched on by
    # `Game.take_action` for callers that haven't migrated to the auction.
    CALLING = "calling"


__all__ = ["Phase"]
