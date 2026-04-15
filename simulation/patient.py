# simulation/patient.py

class Patient:
    def __init__(self, pid, arrival_time, department):
        self.pid          = pid
        self.arrival_time = arrival_time
        self.department   = department
        self.service_start = None
        self.departure_time = None

    @property
    def wait_time(self):
        if self.service_start:
            return self.service_start - self.arrival_time
        return None

    @property
    def sojourn_time(self):
        if self.departure_time:
            return self.departure_time - self.arrival_time
        return None