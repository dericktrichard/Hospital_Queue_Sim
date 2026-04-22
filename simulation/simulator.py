import simpy
import numpy as np
from simulation.patient import Patient

class HospitalSimulator:
    def __init__(self, lam, mu, num_servers=1, sim_hours=8, seed=42, erlang_k=None):
        self.lam        = lam
        self.mu         = mu
        self.k          = num_servers
        self.sim_hours  = sim_hours
        self.seed       = seed
        self.erlang_k   = erlang_k   
        self.patients   = []
        self.queue_log  = [] 

    def _service_time(self, rng):
        if self.erlang_k:
            # Erlang-k: sum of k exponentials each with rate k*mu
            return sum(rng.exponential(1/(self.k * self.mu)) for _ in range(self.erlang_k))
        return rng.exponential(1 / self.mu)

    def _patient_process(self, env, pid, server, rng, dept):
        arrival = env.now
        p = Patient(pid, arrival, dept)
        with server.request() as req:
            yield req
            p.service_start = env.now
            svc = self._service_time(rng)
            yield env.timeout(svc)
            p.departure_time = env.now
        self.patients.append(p)

    def _arrivals(self, env, server, rng, dept):
        pid = 0
        while True:
            iat = rng.exponential(1 / self.lam)
            yield env.timeout(iat)
            self.queue_log.append((env.now, max(0, len(server.queue))))
            env.process(self._patient_process(env, pid, server, rng, dept))
            pid += 1

    def run(self, department="OPD"):
        rng = np.random.default_rng(self.seed)
        env = simpy.Environment()
        server = simpy.Resource(env, capacity=self.k)
        env.process(self._arrivals(env, server, rng, department))
        env.run(until=self.sim_hours)

    def results(self):
        waits    = [p.wait_time for p in self.patients if p.wait_time is not None]
        sojourns = [p.sojourn_time for p in self.patients if p.sojourn_time is not None]
        return {
            "Patients served":            len(self.patients),
            "Avg wait time (min)":        round(np.mean(waits)*60, 2) if waits else 0,
            "Avg sojourn time (min)":     round(np.mean(sojourns)*60, 2) if sojourns else 0,
            "Max wait time (min)":        round(max(waits)*60, 2) if waits else 0,
            "Avg queue length (simulated)": round(np.mean([q for _, q in self.queue_log]), 3),
        }