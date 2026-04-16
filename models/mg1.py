class MG1:
    """
    M/G/1 queue — general service time via Pollaczek-Khinchine formula.
    For Erlang-k: Cs2 = 1/k  (k=1 → exponential, k→∞ → deterministic)
    """
    def __init__(self, lam, mu, Cs2=1.0):
        """
        lam: arrival rate
        mu:  service rate  (1/mean_service_time)
        Cs2: squared coefficient of variation of service time
             Exponential → 1.0
             Erlang-k    → 1/k
             Deterministic → 0.0
        """
        self.lam = lam
        self.mu  = mu
        self.rho = lam / mu
        self.Cs2 = Cs2

    def Lq(self):
        return (self.rho**2 * (1 + self.Cs2)) / (2 * (1 - self.rho))

    def L(self):
        return self.Lq() + self.rho

    def Wq(self):
        return self.Lq() / self.lam

    def W(self):
        return self.Wq() + 1/self.mu

    def summary(self):
        dist = f"Erlang (Cs²={self.Cs2:.2f})" if self.Cs2 != 1 else "Exponential"
        return {
            "Model": "M/G/1 (P-K formula)",
            "Service distribution": dist,
            "λ": self.lam, "μ": self.mu,
            "ρ (utilisation)":          round(self.rho, 4),
            "Lq (queue length)":        round(self.Lq(), 4),
            "L  (in system)":           round(self.L(), 4),
            "Wq (wait in queue, min)":  round(self.Wq()*60, 2),
            "W  (time in system, min)": round(self.W()*60, 2),
            "P0 (idle %)":              round((1-self.rho)*100, 2),
        }