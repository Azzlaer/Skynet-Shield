# Memory Guard — v0.3.0-alpha

Windows-only opt-in SHA-256 verification of stable, caller-owned buffers using Windows CNG (bcrypt). The API is synchronous and does not monitor other processes, scan addresses, modify memory, hook APIs, or perform automatic enforcement.

Use ShieldHashRegion to calculate a reference digest for an authorized immutable buffer, and ShieldVerifyRegion to compare a stable buffer against a trusted expected digest. Return codes: 0 match/success, 1 mismatch, -1 invalid arguments, -2 hashing failure. Size limit 64 MiB per call. The caller must ensure the entire buffer and digest are accessible for the duration of the call, synchronize concurrent writers and preserve the expected digest independently. Arbitrary or dangling pointers are not safe; null checks are not pointer validation.

A locally generated baseline is suitable for diagnostics but not proof of a clean client. A compromised process can modify both the buffer and verifier. Native signed manifest integration and trusted release baselines remain pending. Do not treat a mismatch as conclusive proof of cheating. GameServer must remain authoritative.

CTest covers the SHA-256 known-answer vector for abc, matching and modified buffers, null inputs, empty and oversized buffers. GitHub Actions builds Win32/x64. No MU client integration has been performed.
