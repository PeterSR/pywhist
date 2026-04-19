"""Thin session wrapper over `Game`. Hosts the scoreboard and sit-out policy.

Sit-out rotation is `manual` by default: the caller picks which 4 of N
registered players are active for each hand. `clockwise` and `longest_out`
are scaffolded in `SessionConfig` but only the default is wired here — see
the rule spec §9 for the full mapping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from ..game.events import ScoreEvent
from ..game.game import Game
from ..game.player import Player
from ..game.ruleset import Ruleset
from .scoreboard import Scoreboard
from .session import SessionConfig
from .state import MatchState


@dataclass
class Match:
    state: MatchState = field(default_factory=MatchState)
    _rng: Random = field(default_factory=Random, repr=False, compare=False)
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            self._rng = Random(self.seed)

    # ---- registration & configuration ----

    def register(
        self,
        players: list[Player],
        *,
        ruleset: Ruleset | None = None,
        session_config: SessionConfig | None = None,
    ) -> None:
        self.state.register_players(players)
        if ruleset is not None:
            self.state.ruleset = ruleset
        if session_config is not None:
            self.state.session_config = session_config
        if self.state.next_dealer is None and players:
            self.state.next_dealer = players[0]

    # ---- per-hand lifecycle ----

    def start_hand(self, active: list[Player] | None = None) -> Game:
        """Pick 4 active seats and construct a fresh `Game`. If `active` is
        None, sits out players according to `sit_out_rotation`. Only the
        `manual` mode is wired here (phase 10 scope); other modes fall back
        to "take the first 4 registered".
        """
        if active is None:
            active = list(self.state.registered[:4])
        if len(active) != 4:
            raise ValueError(f"start_hand requires exactly 4 active players; got {len(active)}")

        sitting_out = frozenset(p for p in self.state.registered if p not in active)
        self.state.next_sitting_out = sitting_out

        assert self.state.next_dealer in active or self.state.next_dealer is None
        dealer_index = 0
        if self.state.next_dealer in active:
            dealer_index = active.index(self.state.next_dealer)

        game = Game(ruleset=self.state.ruleset, seed=None)
        game.state = game.initial_state(players=active, dealer_index=dealer_index)
        self.state.current_hand = game.state
        return game

    def finish_hand(self, game: Game) -> None:
        """Apply score deltas from the game's events. Rotate dealer."""
        assert game.state is not None
        self.state.hand_count += 1
        score_events = [e for e in game.state.events if isinstance(e, ScoreEvent)]
        for e in score_events:
            self.state.scoreboard.apply_deltas(e.per_player)

        # Rotate dealer clockwise within the registered roster.
        if self.state.registered:
            idx = (
                self.state.registered.index(self.state.next_dealer)
                if self.state.next_dealer in self.state.registered
                else -1
            )
            self.state.next_dealer = self.state.registered[(idx + 1) % len(self.state.registered)]

        self.state.current_hand = game.state

    # ---- session end ----

    @property
    def has_ended(self) -> bool:
        cfg = self.state.session_config
        if cfg.end_mode == "open":
            return False
        if cfg.end_mode == "fixed_hands":
            if cfg.fixed_hands_count is None:
                return False
            return self.state.hand_count >= cfg.fixed_hands_count
        if cfg.end_mode == "target_points":
            if cfg.target_points is None:
                return False
            return any(v >= cfg.target_points for v in self.state.scoreboard.totals.values())
        # "time": caller enforces externally — match never self-ends on time.
        return False

    @property
    def scoreboard(self) -> Scoreboard:
        return self.state.scoreboard
