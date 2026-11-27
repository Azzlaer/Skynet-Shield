# Architecture

Foundation: explicit C ABI lifecycle, no work during DLL loading, no telemetry, no external process access.

Planned modules: signed client-file manifest and SHA-256 verification; authorized self-integrity checks; authenticated session heartbeat; authoritative GameServer checks for impossible movement, cooldowns and inventory operations; minimal security event reporting; admin review and appeals.

Threat model: client is untrusted, server validates gameplay and never trusts a client-only verdict. No kernel driver, global keyboard capture, VM blocking or automatic bans in baseline. Do not collect unrelated process contents or personal files. Future components require tests, privacy review and an explicit deployment policy.

Integration pending: confirm Main.exe source/loading interface and GameServer protocol. No proprietary reference binaries are included.
