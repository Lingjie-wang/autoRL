"""Coin Arena — a tiny 2-agent grid game (research code, provided as-is).

Two agents move on a small grid collecting coins. Stepping onto a trap
removes that agent for the rest of the episode. Legacy-style API:
- setup() returns a per-agent observation dict
- advance(actions) takes a dict, returns (obs, rewards, done_flags, extra)
- moving into a wall is illegal; legal moves are given per agent in extra
"""

import random

GRID = 5
ACTIONS = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # up, down, right, left


class CoinArena:
    def __init__(self, n_agents=2, max_turns=40):
        self.n_agents = n_agents
        self.max_turns = max_turns
        self.rng = random.Random()

    def _legal(self, pos):
        mask = []
        for dx, dy in ACTIONS:
            nx, ny = pos[0] + dx, pos[1] + dy
            mask.append(1 if 0 <= nx < GRID and 0 <= ny < GRID else 0)
        return mask

    def setup(self):
        self.turn = 0
        self.alive = {f"p{i}": True for i in range(self.n_agents)}
        self.pos = {f"p{i}": [0, i] for i in range(self.n_agents)}
        self.coin = [self.rng.randrange(GRID), self.rng.randrange(GRID)]
        self.trap = [self.rng.randrange(GRID), self.rng.randrange(GRID)]
        return self._obs(), self._masks()

    def _obs(self):
        return {a: (*self.pos[a], *self.coin) for a in self.pos if self.alive[a]}

    def _masks(self):
        return {a: self._legal(self.pos[a]) for a in self.pos if self.alive[a]}

    def advance(self, actions):
        self.turn += 1
        rewards, done = {}, {}
        for a, act in actions.items():
            if not self.alive[a]:
                continue
            dx, dy = ACTIONS[act]
            nx, ny = self.pos[a][0] + dx, self.pos[a][1] + dy
            if 0 <= nx < GRID and 0 <= ny < GRID:
                self.pos[a] = [nx, ny]
            r = 0.0
            if self.pos[a] == self.coin:
                r += 5.0
                self.coin = [self.rng.randrange(GRID), self.rng.randrange(GRID)]
            if self.pos[a] == self.trap:
                r -= 3.0
                self.alive[a] = False  # agent leaves the game
            rewards[a] = r
            done[a] = (not self.alive[a]) or self.turn >= self.max_turns
        extra = {"masks": self._masks(), "turn_limit": self.turn >= self.max_turns}
        return self._obs(), rewards, done, extra
