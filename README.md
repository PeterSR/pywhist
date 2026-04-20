# pywhist

A Python library for **Danish Esmakker Whist** (also known as *Call-ace Whist*) — rules engine, scoring, and an AI-friendly state-view model.

## Features

- **Complete rules engine** for the 4-player call-ace variant: full auction ladder (almindelig / gode / halve / vip / sans, plus nolo contracts), banket, jernhånd redeals, all-4-aces king call, katten exchange, vip flips, halve-trump selection, and marker-card placement.
- **Pure reducer** — `apply(state, action) -> (new_state, events)` is a deterministic function of a seeded RNG. Any hand is reconstructible from `(seed, action_sequence)`.
- **Frozen state + event log** — `GameState` is immutable (`@dataclass(frozen=True, slots=True)`); every state transition emits a typed event, so observers and replay tools never have to diff states.
- **Per-player redacted views** — `GameStateView` hides information the given seat isn't entitled to (other hands, undisclosed partners, undealt cards), ready to ship to clients.
- **Configurable ruleset** — ~19 flags on `Ruleset` cover the rule variations in common circulation; `Ruleset.default()` gives a sensible canonical preset.
- **Match layer** with a real scoreboard, sit-out rotation for sessions of 5+ players, and four session-end modes (open / fixed-hands / target-points / time).
- **Gym-style RL environment** — `whist.ai.WhistEnv` exposes `reset` / `step` / `legal_actions` for single-hand episodes, and `WhistMatchEnv` wraps full matches.
- **JSON wire format** — every `Action`, `Event`, `GameState`, and `GameStateView` roundtrips through `msgspec` schemas, so pywhist plugs into a server or a training harness without custom encoders.
- **Strict typing** — `mypy --strict` clean; PEP 561 `py.typed`.

## Install

Requires Python 3.12+.

```bash
pip install pywhist
```

For local development:

```bash
uv pip install -e ".[dev]"
```

## Quickstart

Drive a hand end-to-end using the mutating `Game` wrapper:

```python
from whist.game import Game

game = Game(seed=0)
game.deal()

while not game.has_ended:
    player = game.current_player
    actions = game.valid_actions(player)
    if not actions:
        break
    game.take_action(player, actions[0])  # pick any legal action

print(game.get_scoreboard())
```

The pure reducer lives in `whist.game.reducer.apply(state, action, *, rng)` — it takes a frozen `GameState` and an `Action` and returns `(new_state, events)`. Search, replay, and batched self-play can skip the `Game` wrapper and call it directly.

Run a single auto-played hand from the terminal:

```bash
pywhist --seed 0 --verbose
```

## RL environment

```python
from whist.ai import WhistEnv

env = WhistEnv()
obs = env.reset(seed=0)
while not obs.done:
    legal = env.legal_actions()
    obs = env.step(legal[0])          # plug in your policy here
print(obs.info["score_deltas"])       # per-player score delta, zero-sum
```

`Observation` carries `view_json` (the current seat's redacted view), `legal_action_ids`, `reward`, `done`, and an optional `info` dict. Feature encoding and action masking are left to the caller.

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy whist
uv run pytest -q
```

## Further reading

- `sources.md` — references to Danish Whist rulebooks used when writing the rules engine.

## License

MIT — see `LICENSE`.
