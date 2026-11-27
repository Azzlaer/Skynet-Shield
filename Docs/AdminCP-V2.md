# AdminCP Enterprise V2 — v0.12.0-alpha

Build with .NET 8 / Visual Studio 2022. Requires the updated Shield Server. The dashboard now queries overview, servers and sessions; failures clear the snapshot. These separate reads are not an atomic snapshot. GameServers lists configured instances and unexpired grants, not physical connectivity. Sessions shows up to 500 unexpired grants from configured instances, with last activity and expiry; no secrets are returned. Security Events filters by server and category; JSON export now respects both filters. Historical events from removed servers remain visible.

Configuration selects and structurally validates a registry XML; local server launch passes its absolute path. Per-instance secrets must already exist in the GUI process environment. The existing development key fields remain required. Registry validation in GUI is preliminary; server validation is authoritative. No dynamic reload or secret persistence.

Anti-Macro and Integrity tabs navigate to filtered reports; they do not edit policy or generate signatures. Database tab reports local file size only, not remote database status or maintenance. Administrative revocation, policy editing, manifest signing UI, full backup/restore, production authorization and interactive Windows tests remain pending. No automatic enforcement. Reference MU repositories unchanged.
