// v1_to_spikes_bridge.cpp —— SPK1 脉冲流的 C++ 发布端
// OpenMV V1 串口包 → 三神经元频率编码 → ZMQ 发布; 与 Python 版 v1_to_spikes.py 等价, 无 Python 环境时替换用。
// 用法: v1_to_spikes_bridge.exe COM4 [--loopback] [--stdout] [--endpoint tcp://*:5566]
//                                   [--topic /robot/input_spikes] [--period 0.02] [--snn-dt 0.0001]
// 帧结构: 三帧 multipart [topic][16B 头 = magic,version,time_step,spike_count][n×12B {i32 neuron, f32 time, f32 basetimestep}]
//         空批只有前两帧; 完整规格见仓库根 PROTOCOL.md。
// 节拍: 固定 --period(默认 20ms) 一窗; 串口读线程只保留最新帧(新数据覆盖旧数据); 每窗发一批(含空批)。
// 注意: basetimestep 必须是接收端仿真步长(--snn-dt), 不是窗口长度; 接收端 step=(int)(time/basetimestep)。
#include <zmq.hpp>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

namespace {

constexpr uint32_t kMagic = 0x53504B31u;  // "SPK1"
constexpr uint32_t kVersion = 1;
constexpr double kBaseHz = 20.0;
constexpr double kErrGainHz = 90.0;
constexpr double kMaxHz = 110.0;

#pragma pack(push, 1)
struct BatchHeader {
    uint32_t magic;
    uint32_t version;
    uint32_t time_step;
    uint32_t spike_count;
};
struct SpikeIO {
    int32_t neuron;
    float time;
    float basetimestep;
};
#pragma pack(pop)
static_assert(sizeof(BatchHeader) == 16, "header must be 16 bytes");
static_assert(sizeof(SpikeIO) == 12, "spike must be 12 bytes");

struct Packet {
    int seq = 0;
    int state = 2;   // -1 左 / 0 中 / +1 右 / 2 丢失
    int err = 0;     // 归一化误差 ×1000
};

// ---------------- V1 解析 ----------------
bool parseV1(const std::string& line, Packet& p) {
    if (line.rfind("V1,", 0) != 0) return false;
    std::vector<std::string> f;
    size_t start = 0;
    while (start <= line.size()) {
        size_t pos = line.find(',', start);
        if (pos == std::string::npos) {
            f.push_back(line.substr(start));
            break;
        }
        f.push_back(line.substr(start, pos - start));
        start = pos + 1;
    }
    if (f.size() != 9) return false;
    try {
        p.seq = std::stoi(f[1]);
        p.state = std::stoi(f[2]);
        p.err = std::stoi(f[3]);
    } catch (...) {
        return false;
    }
    return true;
}

// ---------------- 串口读取: 只保留最新帧 ----------------
class SerialLatestSource {
public:
    bool open(const std::string& port) {
#ifdef _WIN32
        std::string path = "\\\\.\\" + port;
        h_ = CreateFileA(path.c_str(), GENERIC_READ, 0, nullptr, OPEN_EXISTING,
                         FILE_ATTRIBUTE_NORMAL, nullptr);
        if (h_ == INVALID_HANDLE_VALUE) return false;
        DCB dcb{};
        dcb.DCBlength = sizeof(dcb);
        GetCommState(h_, &dcb);
        dcb.BaudRate = CBR_115200;  // USB CDC 忽略波特率
        dcb.ByteSize = 8;
        dcb.Parity = NOPARITY;
        dcb.StopBits = ONESTOPBIT;
        SetCommState(h_, &dcb);
        COMMTIMEOUTS to{};
        to.ReadIntervalTimeout = 50;
        to.ReadTotalTimeoutConstant = 100;
        SetCommTimeouts(h_, &to);
        return true;
#else
        (void)port;
        return false;
#endif
    }

    void start() { th_ = std::thread([this] { run(); }); }

    bool take(Packet& out) {
        std::lock_guard<std::mutex> lock(m_);
        if (!has_) return false;
        out = latest_;
        has_ = false;
        return true;
    }

    void close() {
        stop_ = true;
        if (th_.joinable()) th_.join();
#ifdef _WIN32
        if (h_ != INVALID_HANDLE_VALUE) {
            CloseHandle(h_);
            h_ = INVALID_HANDLE_VALUE;
        }
#endif
    }

    long long frames() const { return frames_; }
    long long malformed() const { return malformed_; }
    long long overwritten() const { return overwritten_; }

private:
    void run() {
#ifdef _WIN32
        std::string buf;
        char tmp[512];
        while (!stop_) {
            DWORD n = 0;
            if (!ReadFile(h_, tmp, sizeof(tmp), &n, nullptr) || n == 0) continue;
            buf.append(tmp, n);
            size_t pos;
            while ((pos = buf.find('\n')) != std::string::npos) {
                std::string line = buf.substr(0, pos);
                buf.erase(0, pos + 1);
                if (!line.empty() && line.back() == '\r') line.pop_back();
                if (line.empty()) continue;
                Packet p;
                if (!parseV1(line, p)) {
                    ++malformed_;
                    continue;
                }
                std::lock_guard<std::mutex> lock(m_);
                if (has_) ++overwritten_;  // 旧帧还没被取走就被覆盖
                latest_ = p;
                has_ = true;
                ++frames_;
            }
            if (buf.size() > 8192) buf.clear();  // 防脏数据撑爆
        }
#endif
    }

    std::mutex m_;
    Packet latest_;
    bool has_ = false;
    std::atomic<bool> stop_{false};
    std::atomic<long long> frames_{0}, malformed_{0}, overwritten_{0};
    std::thread th_;
#ifdef _WIN32
    HANDLE h_ = INVALID_HANDLE_VALUE;
#endif
};

// ---------------- 脉冲编码 ----------------
int neuronOfState(int state) {
    switch (state) {
        case -1: return 0;
        case 0: return 1;
        case 1: return 2;
        default: return -1;  // 丢失
    }
}

std::vector<SpikeIO> encodeWindow(const Packet& p, double t0, double dt, double& phase,
                                  double snnDt) {
    std::vector<SpikeIO> out;
    int neuron = neuronOfState(p.state);
    if (neuron < 0) {
        phase = 0.0;
        return out;
    }
    double hz = std::min(kBaseHz + kErrGainHz * std::min(std::abs(p.err), 1000) / 1000.0,
                         kMaxHz);
    phase += hz * dt;  // 20Hz×20ms=0.4, 两窗发 1 个, 平均速率不失真
    int k = static_cast<int>(phase);
    phase -= k;
    for (int i = 0; i < k; ++i) {
        SpikeIO s;
        s.neuron = neuron;
        s.time = static_cast<float>(t0 + (i + 0.5) * dt / k);
        s.basetimestep = static_cast<float>(snnDt);
        out.push_back(s);
    }
    return out;
}

// ---------------- 主程序 ----------------
struct Args {
    std::string port;
    bool loopback = false;
    bool stdoutOnly = false;
    std::string endpoint = "tcp://*:5566";
    std::string topic = "/robot/input_spikes";
    double period = 0.02;
    double snnDt = 0.0001;
};

const char* kUsage =
    "usage: v1_to_spikes_bridge.exe COM4 [--loopback] [--stdout] "
    "[--endpoint tcp://*:5566] [--topic /robot/input_spikes] "
    "[--period 0.02] [--snn-dt 0.0001]";

bool parseArgs(int argc, char** argv, Args& a) {
    for (int i = 1; i < argc; ++i) {
        std::string s = argv[i];
        if (s == "--loopback") a.loopback = true;
        else if (s == "--stdout") a.stdoutOnly = true;
        else if (s == "--endpoint" && i + 1 < argc) a.endpoint = argv[++i];
        else if (s == "--topic" && i + 1 < argc) a.topic = argv[++i];
        else if (s == "--period" && i + 1 < argc) a.period = std::atof(argv[++i]);
        else if (s == "--snn-dt" && i + 1 < argc) a.snnDt = std::atof(argv[++i]);
        else if (s.rfind("--", 0) == 0) return false;
        else a.port = s;
    }
    if (!a.loopback && a.port.empty()) return false;
    return true;
}

}  // namespace

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    Args args;
    if (!parseArgs(argc, argv, args)) {
        std::puts(kUsage);
        return 1;
    }

    // ZMQ 发布端(PUB bind)
    zmq::context_t ctx(1);
    zmq::socket_t* pub = nullptr;
    if (!args.stdoutOnly) {
        pub = new zmq::socket_t(ctx, zmq::socket_type::pub);
        try {
            pub->bind(args.endpoint);
        } catch (const zmq::error_t& e) {
            std::printf("bind failed: %s (%s)\n", args.endpoint.c_str(), e.what());
            return 1;
        }
        std::printf("publishing -> %s %s (bind)\n", args.endpoint.c_str(),
                    args.topic.c_str());
        // slow joiner: PUB bind 后订阅传播需要时间, 先等 500ms 再发, 否则前几批全丢
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    SerialLatestSource src;
    std::vector<std::pair<int, int>> scenario;  // loopback: (state, err)
    if (args.loopback) {
        scenario = {{-1, 900}, {-1, 400}, {0, 30}, {0, 60}, {1, 500},
                    {1, 950}, {2, 0}, {-1, 200}, {0, 10}, {2, 0}};
        std::printf("loopback: %zu synthetic V1 frames @ %.0fms\n", scenario.size(),
                    args.period * 1000);
    } else {
        if (!src.open(args.port)) {
            std::printf("open serial %s failed\n", args.port.c_str());
            return 1;
        }
        src.start();
        std::printf("serial: %s | read thread started, latest frame overwrites old\n",
                    args.port.c_str());
    }

    long long n = 0, tStep = 0, totalSpikes = 0;
    long long hist[3] = {0, 0, 0};
    double phase = 0.0;
    Packet last;
    bool haveLast = false;
    double baseT = 0.0;
    bool haveBase = false;
    const char* names[3] = {"N0/LEFT", "N1/CENTER", "N2/RIGHT"};

    auto nextTick = std::chrono::steady_clock::now();
    const auto period = std::chrono::duration_cast<std::chrono::steady_clock::duration>(
        std::chrono::duration<double>(args.period));

    for (;;) {
        std::this_thread::sleep_until(nextTick);
        nextTick += period;

        Packet p;
        double now = 0.0;
        if (args.loopback) {
            if (static_cast<size_t>(n) >= scenario.size()) break;
            p.seq = static_cast<int>(n);
            p.state = scenario[n].first;
            p.err = scenario[n].second;
            now = static_cast<double>(tStep) * args.period;
        } else {
            bool got = src.take(p);
            if (!got) {
                if (!haveLast) continue;  // 首帧未到
                p = last;                 // 本窗无新帧: 沿用上次状态
            }
            auto t = std::chrono::steady_clock::now();
            if (!haveBase) {
                baseT = std::chrono::duration<double>(t.time_since_epoch()).count();
                haveBase = true;
            }
            now = std::chrono::duration<double>(t.time_since_epoch()).count() - baseT;
        }
        last = p;
        haveLast = true;

        auto spikes = encodeWindow(p, now, args.period, phase, args.snnDt);
        ++n;
        ++tStep;
        totalSpikes += static_cast<long long>(spikes.size());
        for (const auto& s : spikes) ++hist[s.neuron];

        if (pub) {
            BatchHeader hdr{kMagic, kVersion, static_cast<uint32_t>(tStep),
                            static_cast<uint32_t>(spikes.size())};
            const bool hasBody = !spikes.empty();
            pub->send(zmq::buffer(args.topic), zmq::send_flags::sndmore);
            pub->send(zmq::buffer(&hdr, sizeof(hdr)),
                      hasBody ? zmq::send_flags::sndmore : zmq::send_flags::none);
            if (hasBody) {
                pub->send(zmq::buffer(spikes.data(), spikes.size() * sizeof(SpikeIO)));
            }
        }

        int neuron = neuronOfState(p.state);
        const char* target = neuron >= 0 ? names[neuron] : "LOST/静默";
        std::printf("#%-6d state=%+d %-9s -> %-9s %2zu spikes  cum: %lld批/%lld脉\n",
                    p.seq, p.state, p.state == 2 ? "LOST" : "", target, spikes.size(),
                    tStep, totalSpikes);
    }

    if (!args.loopback) src.close();
    std::printf("\ndone: %lld windows (%lld malformed), %lld batches, %lld spikes  "
                "hist={%lld,%lld,%lld}  overwritten=%lld\n",
                n, src.malformed(), tStep, totalSpikes, hist[0], hist[1], hist[2],
                src.overwritten());
    if (pub) {       // socket 必须先于 context 析构, 否则 zmq_ctx_term 会一直等
        delete pub;
        pub = nullptr;
    }
    return 0;
}
