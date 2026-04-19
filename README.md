# pywhist

A Python library implementing Danish **Esmakker Whist** (also known as *Call-ace Whist*) — the rules engine, scoring, and an AI-friendly state-view model.

`pywhist` is the foundation of a larger project: it provides the authoritative game logic that an online server (`whist-server`) and a trained agent (`whist-ai`) both consume. It aims to be:

- **Correct** — every rule in the [family-rules spec](../.agent-workspace/peters-esmakker-whist-rules.md) is covered, with a growing golden-file regression suite.
- **Inspectable** — every state transition produces an event; hands can be deterministically replayed from `(seed, action_sequence)`.
- **Bot-friendly** — `GameStateView` is per-player redacted; a gym-style `WhistEnv` wraps the library for RL training.

Status: **1.0.0-alpha** — a revamp in progress. See `.agent-workspace/pywhist-assessment.md` and the phased plan at `/home/peter/.claude/plans/plan-away-it-might-lexical-newt.md` for details.

## Install

Requires Python 3.12+.

```bash
uv pip install -e ".[dev]"
```

## Quickstart

```python
from whist.game import Game

game = Game()
game.deal()

while not game.has_ended:
    player = game.current_player
    actions = game.valid_actions(player)
    game.take_action(player, actions[0])  # pick legal action (random here)

print(game.get_scoreboard())
```

Interactive play in the terminal:

```bash
pywhist
```

## Testing

```bash
uv run pytest            # run tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run mypy whist        # type-check
```

## References

- Rules spec (family variant): `../.agent-workspace/peters-esmakker-whist-rules.md`
- General rules research (online canon): `../.agent-workspace/general-esmakker-whist-rules.md`
- Scoring source of truth: [`whist-score`](../whist-score/) (Vue SPA; scoring formulae are ported into `whist.game.scoring`)
- Danish rules reference: `sources.md`

## License

MIT — see `LICENSE`.
