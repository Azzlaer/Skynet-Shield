#include "Shield.h"
#include <atomic>
namespace { std::atomic<bool> initialized{false}; }
uint32_t ShieldApiVersion(void) { return 0x00010000u; }
int ShieldInitialize(void) { initialized.store(true); return 0; }
int ShieldIsInitialized(void) { return initialized.load() ? 1 : 0; }
void ShieldShutdown(void) { initialized.store(false); }
