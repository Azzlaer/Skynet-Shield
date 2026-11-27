#pragma once
#include "Shield.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Only caller-owned, readable, stable buffers. No remote process access.
   Return 0 = success/match, 1 = mismatch, -1 = invalid argument,
   -2 = hashing error. Digest must point to 32 writable/readable bytes. */
SHIELD_API int ShieldHashRegion(const void* data, size_t size, uint8_t digest[32]);
SHIELD_API int ShieldVerifyRegion(const void* data, size_t size, const uint8_t expected[32]);
#ifdef __cplusplus
}
#endif
