#pragma once
#include <stdint.h>
#if defined(_WIN32)
# if defined(SHIELD_BUILD)
#  define SHIELD_API __declspec(dllexport)
# else
#  define SHIELD_API __declspec(dllimport)
# endif
#else
# define SHIELD_API
#endif
#ifdef __cplusplus
extern "C" {
#endif
SHIELD_API uint32_t ShieldApiVersion(void);
SHIELD_API int ShieldInitialize(void);
SHIELD_API int ShieldIsInitialized(void);
SHIELD_API void ShieldShutdown(void);
#ifdef __cplusplus
}
#endif
