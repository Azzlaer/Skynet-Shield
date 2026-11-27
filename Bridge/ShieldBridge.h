#pragma once
#include <stdint.h>
#include <stddef.h>
#if defined(_WIN32)
# if defined(BRIDGE_BUILD)
#  define BRIDGE_API __declspec(dllexport)
# else
#  define BRIDGE_API __declspec(dllimport)
# endif
# define BRIDGE_CALL __cdecl
#else
# define BRIDGE_API
# define BRIDGE_CALL
#endif
#ifdef __cplusplus
extern "C" {
#endif
typedef struct ShieldBridgeContext ShieldBridgeContext;
/* ABI v1. Caller-owned buffers, opaque DLL-owned context, no STL across ABI.
   All functions synchronous. Call on a backend worker, never the game tick.
   Return 0 success, -1 invalid input, -2 transport/internal error,
   -3 unexpected HTTP status, -4 invalid response.
   Context must outlive requests; destroy only after all calls finish. */
BRIDGE_API uint32_t BRIDGE_CALL ShieldBridge_ApiVersion(void);
BRIDGE_API int BRIDGE_CALL ShieldBridge_Init(const wchar_t* host, uint16_t port,
    const char* game_key, ShieldBridgeContext** out);
BRIDGE_API int BRIDGE_CALL ShieldBridge_Login(ShieldBridgeContext* ctx,
    const char* game_session, char* token, size_t token_capacity,
    uint32_t* expires_in, uint32_t* http_status);
BRIDGE_API int BRIDGE_CALL ShieldBridge_Logout(ShieldBridgeContext* ctx,
    const char* game_session, uint32_t* http_status);
BRIDGE_API void BRIDGE_CALL ShieldBridge_Shutdown(ShieldBridgeContext* ctx);
#ifdef __cplusplus
}
#endif
