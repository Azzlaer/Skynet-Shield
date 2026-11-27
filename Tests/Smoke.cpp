#include "Shield.h"
int main() {
    if (ShieldApiVersion() != 0x00010000u || ShieldIsInitialized()) return 1;
    if (ShieldInitialize() != 0 || !ShieldIsInitialized()) return 2;
    if (ShieldInitialize() != 0 || !ShieldIsInitialized()) return 3;
    ShieldShutdown();
    ShieldShutdown();
    return ShieldIsInitialized() ? 4 : 0;
}
