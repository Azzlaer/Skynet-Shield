import unittest
from Server.action_patterns import analyze, TimingPolicy

class TimingTests(unittest.TestCase):
    def test_regular(self):
        report = analyze([i*250 for i in range(41)])
        self.assertEqual(report.score, 100)
        self.assertEqual(report.reason, "regular_timing_review")

    def test_variable(self):
        times = [0]
        for i in range(40):
            times.append(times[-1] + (150 if i % 2 else 350))
        self.assertEqual(analyze(times).reason, "no_regular_timing_flag")

    def test_insufficient(self):
        self.assertEqual(analyze([0, 250, 500]).reason, "insufficient_sample")
        self.assertEqual(analyze(list(range(41))).reason, "insufficient_sample")

    def test_batched(self):
        times = [i*250 for i in range(41)]
        times[20] = times[19]
        self.assertEqual(analyze(times).reason, "ambiguous_clock_or_batch")

    def test_invalid(self):
        for values in ([1, 0], [float("nan")], [-1], [True], list(range(122))):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    analyze(values)
        with self.assertRaises(ValueError):
            TimingPolicy(regular_fraction=1.1)

    def test_configurable(self):
        times = [i*250 + (i%2)*10 for i in range(41)]
        self.assertEqual(analyze(times).reason, "no_regular_timing_flag")
        self.assertEqual(analyze(times, TimingPolicy(tolerance_ms=15)).reason, "regular_timing_review")
