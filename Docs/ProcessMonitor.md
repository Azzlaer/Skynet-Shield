# Process Monitor — v0.4.0-alpha

Windows-only diagnostic inventory of loader-visible modules in the current process using Toolhelp snapshots. No external process enumeration, remote memory inspection, hooks, blocking, telemetry or automatic sanctions.

ShieldVisitOwnModules invokes a caller-provided visitor for each module path. The callback must not throw, modify module loading, or retain the temporary path pointer. Run outside DllMain. A failed enumeration may have delivered partial results; discard those results or label them incomplete.

ShieldClassifyModulePath compares a path with an explicit caller-provided list using ordinal case-insensitive matching. Use independently trusted full paths. This is a textual comparison, not canonicalization or proof of authenticity. Path aliases, truncated paths, legitimate overlays, and changing module state may produce discrepancies. A listed file can still be modified; use signed release manifests for integrity. Manually mapped code may not appear in a loader snapshot. Do not treat unlisted modules as proof of cheating.

The integration must obtain user notice and avoid collecting or uploading unrelated paths. Actual Main.exe integration and trusted release policy remain pending. Tests check current-process enumeration and path classification.
