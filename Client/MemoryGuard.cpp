#include "MemoryGuard.h"
#include <windows.h>
#include <bcrypt.h>
#include <array>
#include <vector>
#include <cstring>

namespace {
constexpr size_t MaxRegion = 64u * 1024u * 1024u;
struct Algorithm {
    BCRYPT_ALG_HANDLE handle = nullptr;
    ~Algorithm() { if (handle) BCryptCloseAlgorithmProvider(handle, 0); }
};
struct Hash {
    BCRYPT_HASH_HANDLE handle = nullptr;
    ~Hash() { if (handle) BCryptDestroyHash(handle); }
};
}

int ShieldHashRegion(const void* data, size_t size, uint8_t digest[32]) {
    if (!data || !digest || size == 0 || size > MaxRegion) return -1;
    try {
        Algorithm algorithm;
        if (BCryptOpenAlgorithmProvider(&algorithm.handle, BCRYPT_SHA256_ALGORITHM, nullptr, 0) < 0) return -2;
        DWORD objectSize = 0, written = 0;
        if (BCryptGetProperty(algorithm.handle, BCRYPT_OBJECT_LENGTH,
            reinterpret_cast<PUCHAR>(&objectSize), sizeof(objectSize), &written, 0) < 0 ||
            written != sizeof(objectSize) || !objectSize) return -2;
        std::vector<UCHAR> object(objectSize);
        Hash hash;
        if (BCryptCreateHash(algorithm.handle, &hash.handle, object.data(), objectSize, nullptr, 0, 0) < 0) return -2;
        auto bytes = static_cast<const UCHAR*>(data);
        if (BCryptHashData(hash.handle, const_cast<PUCHAR>(bytes), static_cast<ULONG>(size), 0) < 0) return -2;
        std::array<UCHAR, 32> result{};
        if (BCryptFinishHash(hash.handle, result.data(), static_cast<ULONG>(result.size()), 0) < 0) return -2;
        std::memcpy(digest, result.data(), result.size());
        return 0;
    } catch (...) {
        return -2;
    }
}

int ShieldVerifyRegion(const void* data, size_t size, const uint8_t expected[32]) {
    if (!expected) return -1;
    std::array<uint8_t, 32> actual{};
    const int status = ShieldHashRegion(data, size, actual.data());
    if (status != 0) return status;
    unsigned difference = 0;
    for (size_t i = 0; i < actual.size(); ++i) difference |= actual[i] ^ expected[i];
    return difference == 0 ? 0 : 1;
}
