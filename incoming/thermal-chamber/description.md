# Thermal Chamber Control

Please integrate this environment so our RL stack can train on it.

## What it is

A chamber starts near ambient temperature (about 20°C, slightly random) and
must be heated to the target temperature (default 65°C) and held there. The
agent controls heater power continuously between 0 (off) and 1 (full power).

## Observations

`start()` and `apply()` return a dict with:

- `temp`: current chamber temperature in °C. Physically it stays roughly
  between 10 and 100 in normal operation; 95+ triggers an overheat shutdown.
- `target`: the fixed target temperature for this episode, in °C.

## Actions

One float in [0, 1]: heater power fraction. Values outside the range are
clipped by the simulator.

## Objective

`apply()` returns a **cost** (second return value): distance from target
divided by 10, so smaller is better. We want the agent to minimize total cost.

## Episode end

The third return value of `apply()` is a status string:

- `"RUNNING"`: keep going
- `"OVERHEAT"`: temperature exceeded 95°C — this is a failure outcome
- `"TIMEOUT"`: 200 steps elapsed — normal end of an episode

## Dependencies

Only numpy.
