# v1_to_arm.py —— 读相机串口的 V1 状态包，把 -1/0/1 经 TCP 转发
# 用法: python v1_to_arm.py [COM4]     依赖: pip install pyserial
#  TCP 连 127.0.0.1:9000，按行读整数

import socket
import sys
import threading

import serial

TCP_PORT = 9000
ERR_ALPHA = 0.35      # 误差EMA：新值权重
CENTER_ENTER = 0.05   # 进中央门限（窄）
CENTER_EXIT = 0.08    # 出中央门限（宽），滞回防边界抖
SIDE_CONFIRM = 2      # 侧向需连续N帧一致才切换

lock = threading.Lock()
client = None
last = None


def accept_loop(srv):
    global client
    while True:
        c, addr = srv.accept()
        with lock:
            client = c
            cur = last
        print("[arm] client connected:", addr)
        if cur is not None:
            try:
                c.sendall(("%d\n" % cur).encode("ascii"))
            except OSError:
                pass


srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", TCP_PORT))
srv.listen(1)
threading.Thread(target=accept_loop, args=(srv,), daemon=True).start()
print("TCP listening on 127.0.0.1:%d ..." % TCP_PORT)

ser = serial.Serial(sys.argv[1] if len(sys.argv) > 1 else "COM4", 115200, timeout=1)
print("listening serial ... (Ctrl+C stop)")

last = None
err_s = 0.0
has_err = False
zone = 2            # 已确认状态：-1/0/1，2=尚未确认
candidate = 2
cand_frames = 0

while True:
    line = ser.readline().decode("ascii", "ignore").strip()
    if not line.startswith("V1,"):
        continue
    f = line.split(",")
    if len(f) != 9:
        continue
    try:
        state = int(f[2])
        err = int(f[3])
    except ValueError:
        continue

    if state == 2:   # 丢失：重置滤波，不发（下游保持最近值）
        err_s = 0.0
        has_err = False
        candidate = 2
        cand_frames = 0
        continue

    e = err / 1000.0
    err_s = e if not has_err else ERR_ALPHA * e + (1 - ERR_ALPHA) * err_s
    has_err = True

    thr = CENTER_EXIT if zone == 0 else CENTER_ENTER
    if abs(err_s) <= thr:
        zone = 0
        candidate = 2
        cand_frames = 0
    else:
        measured = -1 if err_s < 0 else 1
        if measured == candidate:
            cand_frames += 1
        else:
            candidate, cand_frames = measured, 1
        if cand_frames >= SIDE_CONFIRM:
            zone = measured

    if zone == 2 or zone == last:   # 未确认不发；状态没变不重发
        continue
    last = zone
    with lock:
        c = client
    if c is None:
        print("state=%d" % zone)
        continue
    try:
        c.sendall(("%d\n" % zone).encode("ascii"))
        print("state=%d" % zone)
    except OSError:
        with lock:
            client = None
            print("[arm] client 断开，等待重连…")
