#include "ShieldBridge.h"
#include <windows.h>
#include <winhttp.h>
#include <string>
#include <regex>
#include <cstring>
#include <memory>
struct ShieldBridgeContext {
    std::wstring host;
    uint16_t port;
    char key[65]{};
    ~ShieldBridgeContext() { SecureZeroMemory(key,sizeof(key)); }
};
namespace {
struct Http {
    HINTERNET h;
    ~Http() { if(h) WinHttpCloseHandle(h); }
};
bool hex(const char* s) {
    if(!s) return false;
    for(size_t i=0;i<64;++i)
        if(!((s[i]>='0' && s[i]<='9') || (s[i]>='a' && s[i]<='f'))) return false;
    return s[64]==0;
}
bool sessionId(const char* s) {
    if(!s) return false;
    size_t i=0;
    for(;s[i];++i) {
        if(i>=64) return false;
        char c=s[i];
        if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-')) return false;
    }
    return i>0;
}
bool hostName(const wchar_t* s) {
    if(!s) return false;
    size_t i=0, label=0;
    for(;s[i];++i) {
        if(i>=253) return false;
        wchar_t c=s[i];
        if(c==L'.') {
            if(!label || s[i-1]==L'-') return false;
            label=0;
        } else {
            if(!((c>=L'a'&&c<=L'z')||(c>=L'A'&&c<=L'Z')||(c>=L'0'&&c<=L'9')||c==L'-')) return false;
            if((!label&&c==L'-')||++label>63) return false;
        }
    }
    return i&&label&&s[i-1]!=L'-';
}
int post(const ShieldBridgeContext& ctx,const wchar_t* route,const char* id,
         uint32_t& status,std::string& response) {
    Http session{WinHttpOpen(L"ShieldBridge/1",WINHTTP_ACCESS_TYPE_NO_PROXY,
        WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0)};
    if(!session.h) return -2;
    DWORD tls=WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;
#ifdef WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3
    tls|=WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3;
#endif
    if(!WinHttpSetOption(session.h,WINHTTP_OPTION_SECURE_PROTOCOLS,&tls,sizeof(tls))||
       !WinHttpSetTimeouts(session.h,5000,5000,5000,5000)) return -2;
    Http conn{WinHttpConnect(session.h,ctx.host.c_str(),ctx.port,0)};
    if(!conn.h) return -2;
    Http req{WinHttpOpenRequest(conn.h,L"POST",route,nullptr,WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES,WINHTTP_FLAG_SECURE)};
    if(!req.h) return -2;
    DWORD redirect=WINHTTP_OPTION_REDIRECT_POLICY_NEVER;
    DWORD disable=WINHTTP_DISABLE_COOKIES|WINHTTP_DISABLE_AUTHENTICATION;
    if(!WinHttpSetOption(req.h,WINHTTP_OPTION_REDIRECT_POLICY,&redirect,sizeof(redirect))||
       !WinHttpSetOption(req.h,WINHTTP_OPTION_DISABLE_FEATURE,&disable,sizeof(disable))) return -2;
    wchar_t header[160]{};
    const wchar_t prefix[]=L"Authorization: Bearer ";
    const wchar_t suffix[]=L"\r\nContent-Type: application/json\r\n";
    size_t pos=0;
    for(const wchar_t* p=prefix;*p;++p) header[pos++]=*p;
    for(size_t i=0;i<64;++i) header[pos++]=static_cast<wchar_t>(ctx.key[i]);
    for(const wchar_t* p=suffix;*p;++p) header[pos++]=*p;
    std::string body=std::string("{\"game_session\":\"")+id+"\"}";
    BOOL sent=WinHttpSendRequest(req.h,header,static_cast<DWORD>(pos),body.data(),
        static_cast<DWORD>(body.size()),static_cast<DWORD>(body.size()),0);
    SecureZeroMemory(header,sizeof(header));
    if(!sent||!WinHttpReceiveResponse(req.h,nullptr)) return -2;
    DWORD code=0, size=sizeof(code);
    if(!WinHttpQueryHeaders(req.h,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,
        WINHTTP_HEADER_NAME_BY_INDEX,&code,&size,WINHTTP_NO_HEADER_INDEX)) return -2;
    status=code;
    if(code!=201 && code!=204) return -3;
    if(code==204) return 0;
    char chunk[512];
    for(;;) {
        DWORD got=0;
        if(!WinHttpReadData(req.h,chunk,sizeof(chunk),&got)) return -2;
        if(!got) break;
        if(response.size()+got>4096) return -4;
        response.append(chunk,got);
    }
    return 0;
}
}
uint32_t BRIDGE_CALL ShieldBridge_ApiVersion(void) { return 0x00010000u; }
int BRIDGE_CALL ShieldBridge_Init(const wchar_t* host,uint16_t port,const char* key,ShieldBridgeContext** out) {
    if(!out) return -1;
    *out=nullptr;
    if(!hostName(host)||!port||!hex(key)) return -1;
    try {
        auto ctx=std::make_unique<ShieldBridgeContext>();
        ctx->host=host; ctx->port=port; std::memcpy(ctx->key,key,65);
        *out=ctx.release(); return 0;
    } catch(...) { return -2; }
}
int BRIDGE_CALL ShieldBridge_Login(ShieldBridgeContext* ctx,const char* id,char* token,
    size_t capacity,uint32_t* ttl,uint32_t* status) {
    if(status) *status=0;
    if(ttl) *ttl=0;
    if(token&&capacity) token[0]=0;
    if(!ctx||!sessionId(id)||!token||capacity<65||!ttl||!status) return -1;
    try {
        std::string response;
        int rc=post(*ctx,L"/v1/session/issue",id,*status,response);
        if(rc) return rc;
        if(*status!=201) return -3;
        // Strict v1 server response contract (compact JSON, fixed field order).
        static const std::regex pattern(R"json(\{"token":"([0-9a-f]{64})","expires_in":([0-9]{1,5})\})json");
        std::smatch m;
        if(!std::regex_match(response,m,pattern)) return -4;
        unsigned long value=std::stoul(m[2].str());
        if(value<1||value>86400) return -4;
        const std::string grant=m[1].str();
        std::memcpy(token,grant.data(),64);
        token[64]=0; *ttl=static_cast<uint32_t>(value);
        return 0;
    } catch(...) { return -2; }
}
int BRIDGE_CALL ShieldBridge_Logout(ShieldBridgeContext* ctx,const char* id,uint32_t* status) {
    if(status) *status=0;
    if(!ctx||!sessionId(id)||!status) return -1;
    try {
        std::string response;
        int rc=post(*ctx,L"/v1/session/revoke",id,*status,response);
        return rc?rc:(*status==204?0:-3);
    } catch(...) { return -2; }
}
void BRIDGE_CALL ShieldBridge_Shutdown(ShieldBridgeContext* ctx) { delete ctx; }
