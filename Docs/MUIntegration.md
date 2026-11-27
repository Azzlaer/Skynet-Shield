# MU Integration — v0.9.0-alpha

Source-level reference adapters only. No original Ex907 Main.exe or GameServer source was supplied for this change. No binary patching, offsets, injection, packet opcodes or compatibility claims are made.

## Client
Build the Win32 DLL and link its generated import library from the authorized client source. Include Common and Integration/Client, compile SessionWorker.cpp into the host and use SessionWorker outside DllMain. After successful game authentication and secure token delivery, initialize ShieldInitialize(), then Start(trustedShieldHost, newlyIssuedToken). Poll LastResult/LastHttpStatus from the owner thread. Stop before logout, reauthentication or DLL unload; then ShieldShutdown(). Stop joins the worker and can wait for the current network operation, so schedule it outside the render thread. Start/Stop must be serialized by the owner. No auto-ban or gameplay interruption is implemented.

## GameServer
The Python ShieldApi is a reference for the native GameServer developer, not an integrated C++ GameServer plugin. Port its HTTPS contract to the actual authenticated login/logout handlers or invoke it in a trusted backend. Issue only after authenticating the player, use a unique opaque game session identifier, send only the per-session grant to the matching client over a confidential authenticated channel, and revoke on logout. Never put the GameServer service key in the client. Renewal must coordinate stopping the old worker before delivering a new grant; absolute expiry is currently 300 seconds by default. The client stops on HTTP 401/403 and requires a new grant.

## Pending deployment gates
Actual source locations and packet protocol, confidential grant delivery, event submission from native DLL, signed manifest integration, authoritative gameplay validation, calibrated action sampling, HTTPS reverse proxy and rate limits, live interoperability and performance testing. Do not deploy enforcement until these are validated. Test fixtures use a fake heartbeat sender and mocked GameServer requests, not a live TLS connection.
