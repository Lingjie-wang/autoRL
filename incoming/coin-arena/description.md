# Coin Arena (2-agent grid game)

Please integrate this multi-agent environment so our MARL stack can train on it.

## What it is

Two agents move on a 5x5 grid collecting coins. Agents act simultaneously
each turn. Stepping on the trap cell removes that agent for the rest of the
episode; the other keeps playing.

## Agents

- Two agents, ids `p0` and `p1`, homogeneous (same observation and action
  layout).
- An agent that dies (steps on the trap) is dropped from the game; the
  episode continues for survivors.

## Observations (per agent)

A tuple `(my_x, my_y, coin_x, coin_y)`, integers in [0, 4].

## Actions (per agent)

Discrete 0-3: up, down, right, left. Moving into a wall is illegal — the set
of legal actions per agent is provided each turn (see below).

## Action legality

Legality is a per-agent 0/1 list over the 4 actions. `setup()` returns it as
the second value; `advance()` returns it inside the fourth value under
`"masks"`.

## Rewards (per agent)

+5 for collecting a coin, -3 for hitting the trap. This is a reward
(bigger is better), not a cost.

## Episode end

- An agent is done when it dies or when the turn limit (40) is reached.
- The episode ends when all agents are done.

## Dependencies

Standard library only (the env uses `random`).
