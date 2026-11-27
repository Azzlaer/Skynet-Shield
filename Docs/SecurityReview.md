# Security review and integration testing — 0.13.0-alpha

Scope: targeted review of Server/service.py, registry.py, native ShieldBridge transport and AdminCP configuration behavior. Not an independent penetration test or exhaustive audit.

## Changes
- Reject malformed authorization early, duplicate JSON members, non-finite JSON, invalid UTF-8 and excessive nesting.
- Sample session expiry after obtaining the SQLite write transaction, not before lock contention.
- Delete grants of removed instances on service startup. Back up database before changing registry. Only one authoritative registry/process may manage a database. Re-adding an ID requires new authenticated grants. Key rotation for a retained ID still does not revoke its grants automatically.
- Tighten XML size, structure and duplicate credential references.
- Clear stale AdminCP data on invalid connection configuration.
- Add concurrent replay/rotation regressions and real loopback HTTP lifecycle test. These do not exercise native WinHTTP or TLS.

## Release gates
Automated Windows x86/x64 CMake/CTest, .NET build, Python regression tests must pass. Before public deployment: real v140 GameServer host ABI/link test; actual Main.dll integration; authenticated confidential token delivery and renewal; TLS certificate validation end-to-end; bounded queues and rate limits at trusted production proxy; credential rotation and revocation procedures; GUI runtime and recovery tests; load/soak tests; backup/restore drills; review dependency/toolchain support and sign distributables. Current client reports are untrusted; no automatic punishment. Native bridge uses synchronous per-operation timeouts and strict compact response format; caller must coordinate worker lifecycle and prevent stale grants. Do not run wsgiref publicly. No actual MU integration or third-party assessment completed.

Reference repositories and original binaries remain unchanged.
