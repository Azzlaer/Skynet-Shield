#include "ProcessMonitor.h"
#include <windows.h>
#include <tlhelp32.h>
namespace {
struct Snapshot {
    HANDLE handle = INVALID_HANDLE_VALUE;
    ~Snapshot() { if (handle != INVALID_HANDLE_VALUE) CloseHandle(handle); }
};
}
int ShieldVisitOwnModules(ShieldModuleVisitor visitor, void* context) {
    if (!visitor) return -1;
    Snapshot snapshot;
    for (unsigned attempt = 0; attempt < 4; ++attempt) {
        snapshot.handle = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, GetCurrentProcessId());
        if (snapshot.handle != INVALID_HANDLE_VALUE) break;
        if (GetLastError() != ERROR_BAD_LENGTH) return -2;
    }
    if (snapshot.handle == INVALID_HANDLE_VALUE) return -2;
    MODULEENTRY32W entry{};
    entry.dwSize = sizeof(entry);
    if (!Module32FirstW(snapshot.handle, &entry)) return -2;
    do {
        visitor(entry.szExePath, context);
        entry.dwSize = sizeof(entry);
    } while (Module32NextW(snapshot.handle, &entry));
    return GetLastError() == ERROR_NO_MORE_FILES ? 0 : -2;
}
int ShieldClassifyModulePath(const wchar_t* path, const wchar_t* const* allowed, size_t count) {
    if (!path || !*path || (count && !allowed) || count > 4096) return -1;
    for (size_t i = 0; i < count; ++i) {
        if (!allowed[i] || !*allowed[i]) return -1;
    }
    for (size_t i = 0; i < count; ++i) {
        const int result = CompareStringOrdinal(path, -1, allowed[i], -1, TRUE);
        if (!result) return -2;
        if (result == CSTR_EQUAL) return 0;
    }
    return 1;
}
