# AdminCP Enterprise — v0.8.0-alpha

Windows 11 x64, Visual Studio 2022 17.8+ with .NET 8 desktop workload. Open AdminCP/SkynetShield.Admin.csproj or run dotnet build AdminCP/SkynetShield.Admin.csproj -c Release. Launch with dotnet run --project AdminCP/SkynetShield.Admin.csproj.

Settings: choose repository root, trusted Python executable, SQLite path, and separate 64-character lowercase hex service keys. Keys are masked, held in memory, not saved by the GUI. For local development use the default loopback API URL and generate keys. Start Server Control, then refresh Dashboard. For remote services HTTPS is required, standard certificate validation is retained, redirects and proxies disabled. The operator must trust the configured endpoint. The server uses the existing PR #7 API.

Dashboard shows unexpired sessions (not necessarily connected players) and up to 100 recent unverified reports. Security Events supports filtering and JSON export of the entire fetched snapshot. Reports contain opaque game session identifiers; handle exports privately. Console displays sanitized operational messages, not raw child logs. Server Control starts only a local development process and stops only the process it owns, using termination rather than graceful shutdown. Existing independently started servers are not controlled.

Sessions tab explains current API limitations. Individual session management, Integrity Guard GUI, Anti-Macro policy editing, database administration, administrative accounts, production deployment and actual game integration are deferred. No ban controls or automatic enforcement. CI compiles the WinForms project but does not execute interactive GUI tests.
