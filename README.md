# OpenMV 视觉传感器线 · 类脑机械臂项目

科研课堂（类脑计算 + 机械臂）里本人负责的**视觉传感器线**。
板载 OpenMV Cam H7 Plus 采集 → 串口 V1 协议 → PC 端脉冲编码 → ZMQ → SNN 网络 → xMate 机械臂。

> 上游：机器人学讲义；下游：MotionEnergy → SNN → xMate（`RobotAssist_5.0.10.0171`）。

## 目录

```
openmv-vision/
├── PROTOCOL.md     SPK1 脉冲流传输格式完整规格（收发两端唯一依据）
├── scripts/       板载 MicroPython（OpenMV H7 Plus，存为 main.py 或从 IDE 运行）
├── pc/            PC 端 Python：串口翻译、脉冲编码、接收端、离线分析
├── cpp/           C++ 桥接与接收端源码，附构建脚本
└── logs/          课堂串口日志（调参过程的实证记录）
```

## 脉冲流格式

`pc/v1_to_spikes.py` 与 `cpp/v1_to_spikes_bridge.cpp` 发布 / `pc/snn_rx_sim.py` 与
`cpp/spike_rx_demo.cpp` 解析的，都是 [`PROTOCOL.md`](PROTOCOL.md) 定义的 SPK1 格式：
三帧 multipart（topic + 16B 头 + n×12B 脉冲），空批只发两帧，接收端按
`step = (int)(time / basetimestep)` 还原仿真步数。

**这份规格由本仓库完整给出**，四种实现（Python 发 / Python 收 / C++ 发 / C++ 收）
互为交叉验证——任何一端与规格不符，`PROTOCOL.md` §8 的自检就会暴露。

## 硬件与环境

| 项 | 值 |
|---|---|
| 板卡 | OpenMV Cam H7 Plus（OPENMV4P / STM32H743） |
| 传感器 | OV5640（**注意**：站上教程部分参数按 OV7725 写的） |
| 固件 | 4.6.20 |
| IDE | OpenMV IDE (Windows)，串口 COM4，板载 U 盘直挂 |
| 教程 | book.openmv.cc —— **站上示例是新 N6 板的 `csi` API，H7 不可直接抄** |

## 脚本清单

### `scripts/` 板载 MicroPython

| 文件 | 功能 | 状态 |
|---|---|---|
| `helloworld_h7.py` | 出图 + 帧率 | 基准自检 |
| `blobs_h7.py` | 多颜色色块检测 | 双阈值，`TARGET_CODE` 一行切目标 |
| `motion_h7.py` | 坐标 → 速度 / 方向 / 静止判定 | 差分 + EMA(α=0.2)，V_STOP=100 px/s |
| `zone_h7.py` | 色块 + 运动 + 区域判决 三合一 | 输出 V1 同款状态码 左=-1 / 中=0 / 右=1（丢失=LOST） |
| `axis_h7.py` | 归一化坐标系可视化 | 原点=画面中心，x 右正，y 上正 |
| `apriltag_2d_h7.py` | tag id / 中心 / 自转角 | TAG36H11，20.5 fps |
| `apriltag_3d_h7.py` | 6 自由度位姿 | 内参按分辨率自动计算 |
| `template_match_h7.py` | NCC 模板匹配 | 需先放 `template.pgm` 到 U 盘根目录；未实测 |
| `frame_logger_h7.py` | 帧序列落盘 | 图像 + 时间戳 + 坐标存 `/log` |
| `stream_h7.py` | 实时推流 | 灰度 QQVGA，需存为 main.py 脱机运行 |
| `arm_feed_h7.py` | 机械臂位置采集 | 输出 `P,seq,cx,cy,nx,ny,w,px`；COM4 与 SNN 线互斥；未实测 |

### `pc/` 电脑端 Python

| 文件 | 功能 |
|---|---|
| `v1_to_spikes.py` | **交付主线**：串口 V1 包 → 三神经元频率编码 → ZMQ 发布 |
| `snn_rx_sim.py` | SPK1 脉冲流的 Python 接收端，实现 `PROTOCOL.md` §2 帧结构与 §3 步数换算 |
| `pc_receiver.py` | 实时收流（帧差运动能量 demo） |
| `pc_receiver_v1.py` | 解析 V1 文本包（配套板载固件零改动收数） |
| `read_frames.py` | 离线回放：`python read_frames.py <log目录>`，画位置时间轴 + 轨迹图 |
| `v1_to_arm.py` | V1 包 → 机械臂位置流 |
| `test_serial_path.py` / `test_v1_to_spikes.py` | 链路自测 |

### `cpp/`

| 文件 | 说明 |
|---|---|
| `spike_rx_demo.cpp` | **交付主线**：SPK1 脉冲流的 C++ 接收端，格式依据 `PROTOCOL.md` |
| `v1_to_spikes_bridge.cpp` | 备用发送端（功能等价于 Python 版，无 Python 环境时用） |
| `mock_popen_receiver.cpp` | `_popen` + `stdout` 文本行对接的模拟器 |
| `build_*.cmd` | 对应构建脚本 |

> 二进制（`.exe` / `.obj` / `libzmq.dll`）与 `v1_to_spikes.zip` 打包件**不入库**，
> 由 `build_*.cmd` 现场编译。

## 里程碑验收（2026-09-15，四项全过）

| # | 里程碑 | 验收标准 | 结果 |
|---|---|---|---|
| 1 | 色块追球 `blobs_h7.py` | 框+十字跟随绿球 | ✅ 96 fps @ QQVGA |
| 2 | 运动状态 `motion_h7.py` | 静止=STOP、快推=MOVE+方向角 | ✅ 阈值按噪声地板重标定 |
| 3 | AprilTag 2D | 稳定输出 id/cx/cy/rot | ✅ 20.5 fps，静止抖动 cx±1px / rot±0.3° |
| 4 | AprilTag 3D | Tz 随距离单调、倾斜时 Rx/Ry 响应 | ✅ 交叉验证 Rz 与 2D rot 一致（355.5°） |

## 关键测量数据

- **帧率对比**：色块 96 fps vs AprilTag 20.5 fps（QQVGA）→ 高频运动用色块，要位姿用 AprilTag
- **噪声地板实测**（motion 首版，静止小球 @96fps）：幽灵速度 25~76 px/s（像素量化噪声 ÷ 10.4ms 帧间隔），V_STOP=20 全误判；抬到 100 后正常。**阈值必须设在噪声地板之上**
- **9/22 课堂串口日志**（`logs/log_20260922_class.txt`，15110 行 / 21 段运行）：TRACKED 65% vs LOST 35%；zone 左/中/右 = 3477/1559/3132；move 停/动 = 6367/1801
- **运动判据换代的证据链**（`logs/log_20260922_class2.txt`，2104 行）：速度法证伪——静止地板尖刺 max=84.9 与慢推平滑速度 60~90 **分布重叠**，无门限可分；换 12 帧窗净位移后分离——静止 ≤14px、慢推 ≥20px，定 D_ENTER=20 / D_EXIT=10。方法论：方案 → 日志证伪 → 换特征 → 直方图选门限

## 降噪两级框架

**空间域管"这帧看见什么"，时间域管"信不信刚才看见的"**

| 维度 | 措施 | 杀什么噪声 | 本线实测取值 |
|---|---|---|---|
| 空间域 | LAB 阈值窄化 | 颜色相近背景 | 光照变了就重标 |
| 空间域 | 最可信连通域打分选优 | 多目标 / 小杂块 | score = pixels×4 + 矩形度 |
| 空间域 | pixels/area_threshold + merge | 碎框 | 起步 50，加到只剩真目标 |
| 时间域 | 误差 EMA | 逐帧抖动 | α=0.35 |
| 时间域 | 中央滞回（不对称阈值） | 状态边界振荡 | 进 5% / 出 8% |
| 时间域 | 连续帧确认 | 单帧误检 | 2 帧确认 |

> 以上数值为在本线板卡与光照条件下实测调参的结果，与 9/22 课堂日志一致；
> 换场地、换光照需按第五节方法重新标定。

滞回原理 = 施密特触发器：容易进来、不容易出去，状态不抖。

## 踩坑记录（报错信息可搜索）

1. **`AttributeError: no attribute 'CSI'`** → 教程代码是 N6 的 `csi` API。H7 用 `sensor` API：`csi0.reset()`→`sensor.reset()`、`pixformat()`→`set_pixformat()`、`snapshot(time=2000)`→`skip_frames(time=2000)`、`auto_gain()`→`set_auto_gain()`
2. **`TypeError: 'tuple' object isn't callable`** → 固件 4.6.20 里 tag 的 `rect/cx/cy/id/rotation/x_translation` 全是**属性不带括号**
3. **fx/fy 内参不能照抄教程** → 教程按 OV7725（3.984×2.952mm）算，H7 Plus 是 OV5640（3.674×2.738mm）
4. **AprilTag 识别不到** → ①拧镜头筒对焦 ②tag 要占画面 ≥1/8~1/4 ③快速移动因拖影丢帧
5. **模板匹配"必须 SD 卡"** → 老板子情况；H7 Plus 内置 flash 即 U 盘，直接放 pgm
6. **`TARGET_CODE=3` 满屏 LOST** → `find_blobs` 多阈值时 `code()` 是**位掩码**：1=只命中阈值1，2=只命中阈值2，3=**同时命中两个**——绿块 code 恒为 1，永远匹配不上 3。追单色别用 code 过滤
7. **ZMQ socket 必须先于 context 析构** → 否则 `zmq_ctx_term` 永久等待，程序卡死不退出
8. **PUB bind 后要等 ~500ms** 让订阅传播，否则前几批全丢

## 约定与换算

- **图像 y 轴朝下**：`cy` 变小 = 向上运动；数学方向角用 `atan2(-vy, vx)`
- **Tz 为负 = tag 在镜头前方**，取 `|Tz|`；单位 ≈ tag 边长的倍数，精确 cm 需一次标定 `k = 实际距离 ÷ |Tz|`
- **Rx ≈ 180° = tag 竖放正对镜头**
- 角度在 360°↔0° 回绕（359.8→0.0 不是跳变）
- 颜色识别前必须 `set_auto_gain(False)` + `set_auto_whitebal(False)`；光照变了要重标 LAB 阈值
- 丢目标必须重置历史坐标，否则跨帧差分出"瞬移速度"

## 设计决策

- **相机装在 xMate 机械臂上（eye-in-hand）**，球固定在世界系 —— 动镜头不动球
- **MotionEnergy 的输入 = 相机系视网膜流**，现有管线输出 `(t, x, y)` / `(nx, ny)` 即为正确格式，无需世界系补偿
- 神经科学对应：眼球运动引入的视网膜流 = reafference（再传入）
- **世界系真值**（可选）：双标记方案 —— 基准 AprilTag 贴底座 + 球上贴 tag，相对位姿自动抵消相机运动
- **装上臂后必须重测噪声地板**：臂振动会抬高底噪

## 免责与归属

- `scripts/`、`pc/`、`cpp/` 下的脚本均为本人编写。
- **SPK1 脉冲流格式的完整规格见 [`PROTOCOL.md`](PROTOCOL.md)**——本仓库自带收发两端
  实现与全部自检手段，读这一份即可独立复现，不依赖任何外部文档。
