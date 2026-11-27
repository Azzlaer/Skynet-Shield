"""Diagnostic timing analysis of server-observed, accepted game actions."""
from dataclasses import dataclass
from statistics import median
import math

@dataclass(frozen=True)
class TimingPolicy:
    min_intervals: int = 30
    max_intervals: int = 120
    tolerance_ms: float = 5.0
    regular_fraction: float = 0.95
    min_span_ms: float = 5000.0

    def __post_init__(self):
        if not (type(self.min_intervals) is int and type(self.max_intervals) is int
                and 10 <= self.min_intervals <= self.max_intervals <= 1000):
            raise ValueError("Invalid sample limits")
        if not (0 < self.tolerance_ms <= 100 and 0.5 <= self.regular_fraction <= 1
                and 0 < self.min_span_ms <= 600000):
            raise ValueError("Invalid timing policy")

@dataclass(frozen=True)
class TimingReport:
    samples: int
    median_ms: float | None
    regular_fraction: float
    score: int
    reason: str

def analyze(timestamps_ms, policy=TimingPolicy()):
    """One session, one action type, same monotonic server clock.
    Caller supplies at most max_intervals + 1 timestamps in arrival order.
    Score describes regularity, NOT probability of cheating.
    """
    times = list(timestamps_ms)
    if len(times) > policy.max_intervals + 1:
        raise ValueError("Too many samples")
    if any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in times):
        raise ValueError("Invalid timestamp")
    intervals = [b-a for a,b in zip(times, times[1:])]
    if any(d < 0 or not math.isfinite(d) for d in intervals):
        raise ValueError("Timestamps must be monotonic")
    if len(intervals) < policy.min_intervals or sum(intervals) < policy.min_span_ms:
        return TimingReport(len(intervals), None, 0.0, 0, "insufficient_sample")
    center = median(intervals)
    # Batched or quantized network observations are not reliable evidence.
    if center <= policy.tolerance_ms or any(d == 0 for d in intervals):
        return TimingReport(len(intervals), center, 0.0, 0, "ambiguous_clock_or_batch")
    fraction = sum(abs(d-center) <= policy.tolerance_ms for d in intervals) / len(intervals)
    score = round(100*fraction)
    return TimingReport(len(intervals), center, fraction, score,
        "regular_timing_review" if fraction >= policy.regular_fraction else "no_regular_timing_flag")
