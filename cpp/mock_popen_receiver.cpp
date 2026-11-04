// mock_popen_receiver.cpp —— 文本回退通道的最小验证器(PROTOCOL.md §7)
// 场景: 宿主程序以 _popen 拉起 Python 子进程 → fgets 逐行 → sscanf("DIR,%d") 取状态。
// 用途: 在本机验证这条通道能通, 不需要真实宿主工程。
// 用法: mock_popen_receiver.exe ["可选自定义命令"] [--n 100]
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif
    setvbuf(stdout, nullptr, _IONBF, 0);

    // 默认命令指向仓库内 pc/ 下的发布端; 若从别处启动可用自定义命令参数指定
    std::string cmd =
        "python -u ..\\pc\\v1_to_spikes.py --loopback --stdout --repeat --quiet";
    int limit = 100;
    for (int i = 1; i < argc; ++i) {
        std::string s = argv[i];
        if (s == "--n" && i + 1 < argc) limit = std::atoi(argv[++i]);
        else cmd = s;
    }

    std::printf("_popen: %s\n", cmd.c_str());
    FILE* pipe = _popen(cmd.c_str(), "r");
    if (!pipe) {
        std::printf("popen failed\n");
        return 1;
    }

    char line[128];
    int parsed = 0, bad = 0, other = 0, last = -99;
    int hist[4] = {0, 0, 0, 0};  // -1,0,1,2
    auto t0 = std::chrono::steady_clock::now();
    auto elapsed = [&] {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0)
            .count();
    };

    while (std::fgets(line, sizeof(line), pipe)) {
        int state = 0;
        if (std::sscanf(line, "DIR,%d", &state) == 1) {  // PROTOCOL.md §7 文本通道
            if (state < -1 || state > 2) {
                ++bad;
                std::printf("[BAD] out-of-range state=%d\n", state);
            } else {
                if (parsed < 5 || state != last)
                    std::printf("  got DIR,%d  (t=%.2fs)\n", state, elapsed());
                ++parsed;
                ++hist[state + 1];
                last = state;
            }
        } else {
            ++other;  // 非 DIR 行(调试输出): 按规格忽略
        }
        if (parsed >= limit) break;
    }
    _pclose(pipe);

    std::printf("\nparsed=%d  bad=%d  ignored_lines=%d  elapsed=%.2fs  ~%.1f Hz\n",
                parsed, bad, other, elapsed(), parsed / (elapsed() > 0 ? elapsed() : 1));
    std::printf("hist: left(-1)=%d  center(0)=%d  right(1)=%d  lost(2)=%d\n",
                hist[0], hist[1], hist[2], hist[3]);
    std::printf("verdict: %s\n",
                (parsed > 0 && bad == 0) ? "PASS" : "FAIL");
    return 0;
}
