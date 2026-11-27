#include "SecureCommunication.h"
#include <string>
int main() {
    uint32_t status = 99;
    const std::wstring token(64, L'a');
    if (ShieldSendHeartbeat(L"https://example.org", token.c_str(), 1, &status) != -1 || status) return 1;
    if (ShieldSendHeartbeat(L"example.org", L"bad", 1, &status) != -1) return 2;
    if (ShieldSendHeartbeat(L"example.org", token.c_str(), 0, &status) != -1) return 3;
    if (ShieldSendHeartbeat(L"example.org", token.c_str(), 1, nullptr) != -1) return 4;
    if (ShieldSendHeartbeat(L"-example.org", token.c_str(), 1, &status) != -1) return 5;
    return 0;
}
