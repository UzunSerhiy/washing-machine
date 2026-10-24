import time


class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()
