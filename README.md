# Skynet Shield

Independent client integrity and fair-play project for Skynet MU (Ex907 / 0.97k). Early development; not a production anti-cheat.

## Build (Visual Studio 2022, Desktop development with C++)

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A Win32
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```
Use a separate build directory and -A x64 for native x64 testing. The MU client requires matching DLL architecture. Load only through an authorized integration; no LayerShield ABI compatibility is claimed.

## Alpha distribution

Download the Windows ZIP from a successful Alpha distribution packages workflow. See [Spanish installation guide](Docs/Installation.es.md) and [security release gates](Docs/SecurityReview.md). No automatic deployment or GitHub Release publishing.

## Roadmap
See Docs/Architecture.md. No automatic bans or background scanning in this release.
