#include "SecureCommunication.h"
#include <windows.h>
#include <winhttp.h>
#include <string>
#include <cwchar>
namespace {
struct Http {
    HINTERNET handle = nullptr;
    ~Http() { if (handle) WinHttpCloseHandle(handle); }
};
bool validHost(const wchar_t* host) {
    if (!host) return false;
    size_t n = 0, label = 0;
    for (; host[n]; ++n) {
        if (n >= 253) return false;
        const wchar_t c = host[n];
        if (c == L'.') {
            if (!label || host[n-1] == L'-') return false;
            label = 0;
        } else {
            if (!((c >= L'a' && c <= L'z') || (c >= L'A' && c <= L'Z') ||
                  (c >= L'0' && c <= L'9') || c == L'-')) return false;
            if ((!label && c == L'-') || ++label > 63) return false;
        }
    }
    return n && label && host[n-1] != L'-';
}
bool validToken(const wchar_t* token) {
    if (!token) return false;
    for (size_t i=0; i<64; ++i)
        if (!((token[i] >= L'0' && token[i] <= L'9') ||
              (token[i] >= L'a' && token[i] <= L'f'))) return false;
    return token[64] == 0;
}
}
int ShieldSendHeartbeat(const wchar_t* host, const wchar_t* token,
                        uint64_t sequence, uint32_t* status) {
    if (!status) return -1;
    *status = 0;
    if (!validHost(host) || !validToken(token) || !sequence) return -1;
    try {
        Http session{WinHttpOpen(L"SkynetShield/0.5", WINHTTP_ACCESS_TYPE_NO_PROXY,
                                 WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0)};
        if (!session.handle) return -2;
        DWORD protocols = WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;
#ifdef WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3
        protocols |= WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3;
#endif
        if (!WinHttpSetOption(session.handle, WINHTTP_OPTION_SECURE_PROTOCOLS,
                              &protocols, sizeof(protocols))) return -2;
        if (!WinHttpSetTimeouts(session.handle, 5000, 5000, 5000, 5000)) return -2;
        Http connection{WinHttpConnect(session.handle, host, INTERNET_DEFAULT_HTTPS_PORT, 0)};
        if (!connection.handle) return -2;
        Http request{WinHttpOpenRequest(connection.handle, L"POST", L"/v1/heartbeat",
            nullptr, WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE)};
        if (!request.handle) return -2;
        DWORD redirect = WINHTTP_OPTION_REDIRECT_POLICY_NEVER;
        if (!WinHttpSetOption(request.handle, WINHTTP_OPTION_REDIRECT_POLICY,
                              &redirect, sizeof(redirect))) return -2;
        DWORD disable = WINHTTP_DISABLE_COOKIES | WINHTTP_DISABLE_AUTHENTICATION;
        if (!WinHttpSetOption(request.handle, WINHTTP_OPTION_DISABLE_FEATURE, &disable, sizeof(disable))) return -2;
        const std::wstring headers = std::wstring(L"Authorization: Bearer ") + token +
            L"\r\nContent-Type: application/json\r\n";
        const std::string body = "{\"sequence\":" + std::to_string(sequence) + "}";
        if (!WinHttpSendRequest(request.handle, headers.c_str(), static_cast<DWORD>(headers.size()),
                const_cast<char*>(body.data()), static_cast<DWORD>(body.size()),
                static_cast<DWORD>(body.size()), 0) ||
            !WinHttpReceiveResponse(request.handle, nullptr)) return -2;
        DWORD code = 0, size = sizeof(code);
        if (!WinHttpQueryHeaders(request.handle, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
             WINHTTP_HEADER_NAME_BY_INDEX, &code, &size, WINHTTP_NO_HEADER_INDEX)) return -2;
        *status = code;
        return code == 204 ? 0 : 1;
    } catch (...) { return -2; }
}
