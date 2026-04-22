class MM1:
    def __init__(self, lam, mu):
        """
        lam: arrival rate (customers/hr)
        mu:  service rate (customers/hr)
        """
        self.lam = lam
        self.mu = mu
        self.rho = lam / mu

    def validate(self):
        if self.rho >= 1:
            raise ValueError(f"System unstable: ρ = {self.rho:.3f} ≥ 1")

    def Lq(self):   # Avg queue length
        return self.rho**2 / (1 - self.rho)

    def L(self):    # Avg number in system
        return self.rho / (1 - self.rho)

    def Wq(self):   # Avg waiting time in queue (hrs)
        return self.Lq() / self.lam

    def W(self):    # Avg time in system (hrs)
        return self.L() / self.lam

    def P0(self):   # Probability system is idle
        return 1 - self.rho

    def Pn(self, n): # Probability of n customers in system
        return (1 - self.rho) * (self.rho ** n)

    def P_more_than(self, n):
        return self.rho ** (n + 1)

    def summary(self):
        self.validate()
        return {
            "Model": "M/M/1",
            "λ (arrival rate)": self.lam,
            "μ (service rate)": self.mu,
            "ρ (utilisation)": round(self.rho, 4),
            "Lq (queue length)": round(self.Lq(), 4),
            "L  (in system)":    round(self.L(), 4),
            "Wq (wait in queue, hrs)": round(self.Wq(), 4),
            "Wq (wait in queue, min)": round(self.Wq()*60, 2),
            "W  (time in system, hrs)": round(self.W(), 4),
            "P0 (idle %)":       round(self.P0()*100, 2),
        }