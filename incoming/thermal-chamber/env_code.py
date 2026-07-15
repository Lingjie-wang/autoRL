"""Thermal chamber simulator (research code, provided as-is)."""

import numpy as np


class ThermalChamber:
    """Heat a chamber to the target temperature and hold it there."""

    def __init__(self, target=65.0, dt=1.0):
        self.target = target
        self.dt = dt

    def start(self):
        self.temp = 20.0 + np.random.uniform(-2.0, 2.0)  # ambient start
        self.t = 0
        return {"temp": self.temp, "target": self.target}

    def apply(self, power):
        power = float(np.clip(power, 0.0, 1.0))
        heating = 8.0 * power
        cooling = 0.1 * (self.temp - 20.0)
        noise = np.random.normal(0.0, 0.3)
        self.temp += (heating - cooling) * self.dt / 5.0 + noise
        self.t += 1

        cost = abs(self.temp - self.target) / 10.0
        status = "RUNNING"
        if self.temp > 95.0:
            status = "OVERHEAT"
        elif self.t >= 200:
            status = "TIMEOUT"
        return {"temp": self.temp, "target": self.target}, cost, status
