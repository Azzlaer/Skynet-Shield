#include "ProcessMonitor.h"
#include <windows.h>
#include <cwchar>
struct State { unsigned count = 0; bool found = false; };
void visit(const wchar_t* path, void* context) {
    auto& state = *static_cast<State*>(context);
    ++state.count;
    const wchar_t* slash = std::wcsrchr(path, L'\\');
    if (CompareStringOrdinal(slash ? slash+1 : path, -1, L"SkynetShield.dll", -1, TRUE) == CSTR_EQUAL)
        state.found = true;
}
int main() {
    State state;
    if (ShieldVisitOwnModules(visit, &state) || !state.count || !state.found) return 1;
    if (ShieldVisitOwnModules(nullptr, nullptr) != -1) return 2;
    const wchar_t* allowed[] = {L"C:\\Game\\Test.dll"};
    if (ShieldClassifyModulePath(L"c:\\game\\test.DLL", allowed, 1) != 0) return 3;
    if (ShieldClassifyModulePath(L"C:\\Other\\Test.dll", allowed, 1) != 1) return 4;
    if (ShieldClassifyModulePath(nullptr, allowed, 1) != -1) return 5;
    if (ShieldClassifyModulePath(L"test.dll", nullptr, 1) != -1) return 6;
    if (ShieldClassifyModulePath(L"test.dll", nullptr, 0) != 1) return 7;
    return 0;
}
