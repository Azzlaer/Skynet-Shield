#include "SessionWorker.h"
#include <atomic>
#include <chrono>
#include <thread>

namespace {
std::atomic<unsigned> calls{0};
int fake(const wchar_t*, const wchar_t*, uint64_t seq, uint32_t* status) {
    ++calls;
    *status = seq == 1 ? 401 : 500;
    return 1;
}
}
int main() {
    skynet::SessionWorker worker(fake);
    if (worker.Start(L"example.test", L"bad", 1)) return 1;
    if (!worker.Start(L"example.test", std::wstring(64,L'a'), 1)) return 2;
    for (int i=0; i<200 && worker.LastHttpStatus()!=401; ++i)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    worker.Stop();
    if (calls != 1 || worker.LastHttpStatus()!=401 || worker.LastResult()!=1) return 3;
    worker.Stop();
    return 0;
}
