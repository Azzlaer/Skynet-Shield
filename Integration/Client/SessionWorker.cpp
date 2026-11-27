#include "SessionWorker.h"
#include <algorithm>
#include <limits>
#include <utility>

namespace skynet {
bool SessionWorker::Start(std::wstring host, std::wstring token, unsigned intervalSeconds) {
    if (worker_.joinable() || !sender_ || host.empty() || token.size() != 64 ||
        intervalSeconds < 1 || intervalSeconds > 60 ||
        !std::all_of(token.begin(), token.end(), [](wchar_t c) {
            return (c >= L'0' && c <= L'9') || (c >= L'a' && c <= L'f');
        })) return false;
    stopping_ = false;
    result_.store(-3);
    status_.store(0);
    try {
        worker_ = std::thread([this, host=std::move(host), token=std::move(token), intervalSeconds] {
            uint64_t sequence = 1;
            for (;;) {
                { std::lock_guard<std::mutex> guard(mutex_); if (stopping_) break; }
                uint32_t http = 0;
                const int result = sender_(host.c_str(), token.c_str(), sequence, &http);
                status_.store(http);
                result_.store(result);
                if (http == 401 || http == 403 || result == -1 ||
                    sequence == (std::numeric_limits<uint64_t>::max)()) break;
                ++sequence; // Even an uncertain response may have consumed the sequence.
                std::unique_lock<std::mutex> lock(mutex_);
                if (wake_.wait_for(lock, std::chrono::seconds(intervalSeconds),
                    [this]{ return stopping_; })) break;
            }
        });
        return true;
    } catch (...) { return false; }
}
void SessionWorker::Stop() {
    { std::lock_guard<std::mutex> guard(mutex_); stopping_ = true; }
    wake_.notify_all();
    if (worker_.joinable()) worker_.join();
}
}
