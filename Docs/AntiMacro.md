# Anti-Macro System — v0.6.0-alpha

Reference server-side diagnostic for regular timing of accepted in-game actions. No keyboard capture, external process inspection, client-side hooks, automated sanctions or telemetry upload.

Collect timestamps from the same monotonic server clock, separated by authenticated game session and action type. Pass a bounded window to analyze(). Defaults: 30 minimum intervals, 120 maximum intervals, 5 ms tolerance around median, 95% regularity review threshold, minimum 5 s observation span. These are illustrative defaults, not calibrated enforcement thresholds. The score is percentage of intervals within tolerance, not probability of cheating. Short or batched observations are treated as inconclusive.

Exclude server-generated actions, legal auto-attack, cooldown-driven actions and accessibility accommodations from review. Network jitter, tick quantization, input buffering and ordinary repetitive gameplay can create misleading patterns. A timing flag alone is not evidence of cheating. Corroborate with authoritative game rules and human review; do not automatically ban or disconnect players. Test on real legitimate play before deployment.

The module accepts timing windows only. No player identifiers or raw keyboard data are needed. Integration, collection, retention policy, rate checks, sequence analysis, and administrative review UI remain pending. Synthetic tests exercise regular/variable windows and ambiguous inputs; they do not measure real-world accuracy.
