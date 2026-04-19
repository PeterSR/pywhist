"""Plain-text CLI driver — runs a match, prints hand-by-hand results.

Phase 11 delivers a minimum-viable interactive entry point:

- `pywhist` launches a 4-player, single-hand game driven by a random AI for
  all seats. It plays the hand to completion and prints the scoreboard.
- The heavy interactive path (human input, seat config, pretty rendering)
  remains deferred — this scaffold keeps the CLI reachable without shipping
  a TUI that would need near-constant maintenance against the reducer.
"""

from __future__ import annotations

import argparse
import random
import sys

from . import __version__
from .game.actions import BaseAction, JernhaandDeclineAction
from .game.game import Game
from .game.phase import Phase


def _pick_random(actions: list[BaseAction], rng: random.Random) -> BaseAction:
    return rng.choice(actions)


def _play_one_hand(seed: int, verbose: bool) -> Game:
    rng = random.Random(seed)
    game = Game(seed=seed)
    game.deal()

    safety = 500
    while not game.has_ended and safety > 0:
        state = game.state
        assert state is not None
        if state.phase == Phase.DEALING and state.jernhaand_pending:
            p = next(iter(state.jernhaand_pending))
            game.take_action(p, JernhaandDeclineAction(p))
            safety -= 1
            continue
        actions = game.valid_actions(game.current_player)
        if not actions:
            break
        action = _pick_random(actions, rng)
        if verbose:
            print(f"[{state.phase.value}] {game.current_player.name}: {action}")
        game.take_action(game.current_player, action)
        safety -= 1

    return game


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pywhist",
        description="Danish Esmakker Whist — minimal auto-play CLI.",
    )
    parser.add_argument("--version", action="version", version=f"pywhist {__version__}")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument("--verbose", action="store_true", help="print each action as it happens")
    args = parser.parse_args(argv)

    game = _play_one_hand(args.seed, args.verbose)
    state = game.state
    assert state is not None
    print()
    print(f"Final phase: {state.phase.value}")
    print(f"Trump: {state.trump.code}  Partner-ace: {state.partner_ace.code}")
    print(f"Tricks played: {len(state.tricks)}")
    scoreboard = game.get_scoreboard()
    if scoreboard:
        print("Tricks per team:")
        for team, count in scoreboard.items():
            names = ", ".join(p.name for p in team)
            print(f"  {names:<30} {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
