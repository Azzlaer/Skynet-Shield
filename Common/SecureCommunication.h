#pragma once
#include "Shield.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Synchronous HTTPS heartbeat to a trusted configured DNS host, port 443.
   token: 64 lowercase hex characters, issued by server.
   sequence: positive, increasing per session. No automatic retry.
   Returns 0 for HTTP 204, 1 for other HTTP responses, -1 for invalid
   arguments, -2 for transport failure. status receives HTTP code or zero.
   Call outside DllMain and off the game render thread. */
SHIELD_API int ShieldSendHeartbeat(const wchar_t* host, const wchar_t* token,
    uint64_t sequence, uint32_t* status);
#ifdef __cplusplus
}
#endif
