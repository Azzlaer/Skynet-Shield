#include "ShieldBridge.h"
#include <string>
int main() {
    if(ShieldBridge_ApiVersion()!=0x00010000u) return 1;
    std::string key(64,'a');
    ShieldBridgeContext* ctx=nullptr;
    if(ShieldBridge_Init(L"https://example.test",443,key.c_str(),&ctx)!=-1||ctx) return 2;
    if(ShieldBridge_Init(L"example.test",443,"bad",&ctx)!=-1||ctx) return 3;
    if(ShieldBridge_Init(L"example.test",443,key.c_str(),&ctx)!=0||!ctx) return 4;
    char token[65]{}; uint32_t ttl=1,status=1;
    if(ShieldBridge_Login(ctx,"bad/id",token,sizeof(token),&ttl,&status)!=-1||ttl||status) return 5;
    if(ShieldBridge_Login(ctx,"valid",token,10,&ttl,&status)!=-1) return 6;
    if(ShieldBridge_Logout(ctx,"",&status)!=-1) return 7;
    ShieldBridge_Shutdown(ctx);
    ShieldBridge_Shutdown(nullptr);
    return 0;
}
