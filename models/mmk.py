# models/mmk.py
# Model VII: M/M/K : ∞ / FCFS

import math

class MMK:
    def __init__(self, lam, mu, k):
        self.lam = lam
        self.mu  = mu
        self.k   = k
        self.rho = lam / (k * mu)  # server utilisation

    def validate(self):
        if self.rho >= 1:
            raise ValueError(f"System unstable: ρ = {self.rho:.3f} ≥ 1")

    def _P0(self):
        r = self.lam / self.mu
        k = self.k
        sum_terms = sum((r**n) / math.factorial(n) for n in range(k))
        last_term = (r**k) / (math.factorial(k) * (1 - self.rho))
        return 1 / (sum_terms + last_term)

    def P0(self):
        return self._P0()

    def Lq(self):
        r   = self.lam / self.mu
        k   = self.k
        P0  = self._P0()
        return (P0 * (r**k) * self.rho) / (math.factorial(k) * (1 - self.rho)**2)

    def L(self):
        return self.Lq() + (self.lam / self.mu)

    def Wq(self):
        return self.Lq() / self.lam

    def W(self):
        return self.Wq() + 1/self.mu

    def summary(self):
        self.validate()
        return {
            "Model": f"M/M/{self.k}",
            "λ": self.lam, "μ": self.mu, "K servers": self.k,
            "ρ (utilisation)":          round(self.rho, 4),
            "P0 (idle %)":              round(self.P0()*100, 2),
            "Lq (queue length)":        round(self.Lq(), 4),
            "L  (in system)":           round(self.L(), 4),
            "Wq (wait in queue, min)":  round(self.Wq()*60, 2),
            "W  (time in system, min)": round(self.W()*60, 2),
        }