#pragma once
#include "Shield.h"
#include <stddef.h>
#include <wchar.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Current process only. Callback paths are valid during the callback.
   Return 0 on complete enumeration, -1 invalid argument, -2 OS failure.
   Call outside DllMain. Callback must not throw or change module loading. */
typedef void (*ShieldModuleVisitor)(const wchar_t* path, void* context);
SHIELD_API int ShieldVisitOwnModules(ShieldModuleVisitor visitor, void* context);
/* Compare full paths using ordinal case-insensitive comparison.
   0 = listed, 1 = unlisted, -1 = invalid input, -2 = comparison error.
   Path match is diagnostic only, not an authenticity guarantee. */
SHIELD_API int ShieldClassifyModulePath(const wchar_t* path, const wchar_t* const* allowed, size_t count);
#ifdef __cplusplus
}
#endif
