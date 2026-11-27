#pragma once
#include "SecureCommunication.h"
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>
#include <thread>

namespace skynet {
// Source-level adapter. Owner serializes Start/Stop and destroys before DLL unload.
// Each Start requires a newly issued token. Never call from DllMain.
class SessionWorker {
public:
    using Sender = int (*)(const wchar_t*, const wchar_t*, uint64_t, uint32_t*);
    explicit SessionWorker(Sender sender = ShieldSendHeartbeat) : sender_(sender) {}
    ~SessionWorker() { Stop(); }
    SessionWorker(const SessionWorker&) = delete;
    SessionWorker& operator=(const SessionWorker&) = delete;
    bool Start(std::wstring host, std::wstring token, unsigned intervalSeconds = 15);
    void Stop();
    int LastResult() const { return result_.load(); }
    uint32_t LastHttpStatus() const { return status_.load(); }
private:
    Sender sender_;
    std::thread worker_;
    std::mutex mutex_;
    std::condition_variable wake_;
    bool stopping_ = false;
    std::atomic<int> result_{-3};
    std::atomic<uint32_t> status_{0};
};
}
