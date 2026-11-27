#include "MemoryGuard.h"
#include <array>
int main() {
    std::array<unsigned char, 3> region{{'a','b','c'}};
    const std::array<uint8_t,32> expected{{
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
        0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,
        0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad}};
    std::array<uint8_t,32> actual{};
    if (ShieldHashRegion(region.data(), region.size(), actual.data()) != 0 || actual != expected) return 1;
    if (ShieldVerifyRegion(region.data(), region.size(), expected.data()) != 0) return 2;
    region[0] = 'd';
    if (ShieldVerifyRegion(region.data(), region.size(), expected.data()) != 1) return 3;
    if (ShieldHashRegion(nullptr, 3, actual.data()) != -1) return 4;
    if (ShieldHashRegion(region.data(), 0, actual.data()) != -1) return 5;
    if (ShieldHashRegion(region.data(), region.size(), nullptr) != -1) return 6;
    if (ShieldVerifyRegion(region.data(), region.size(), nullptr) != -1) return 7;
    if (ShieldHashRegion(region.data(), 64u*1024u*1024u+1u, actual.data()) != -1) return 8;
    return 0;
}
