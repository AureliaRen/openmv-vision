# pc_receiver.py —— 电脑端：收 OpenMV 推流，实时算帧差运动能量（ME 的占位demo）
# 用法: python pc_receiver.py COM4        (Ctrl+C 停止)
# 依赖: pip install pyserial numpy
import sys
import time
import struct
import numpy as np
import serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM4"

HEADER = struct.Struct("<2sHHB")
SYNC = b"\xAA\x55"
W, H = 160, 120
NBYTES = W * H

def read_exact(ser, buf, nbytes):
    """从串口凑够 nbytes 字节；超时返回 None"""
    while len(buf) < nbytes:
        chunk = ser.read(min(8192, nbytes - len(buf)))
        if not chunk:
            return None, buf
        buf += chunk
    return buf[:nbytes], buf[nbytes:]

ser = serial.Serial(port, 921600, timeout=1.0)   # USB CDC 忽略波特率，API 必填
print("listening on", port, "... (Ctrl+C to stop)")

buf = b""
n = 0
t0 = None
prev = None
try:
    while True:
        hdr, buf = read_exact(ser, buf, HEADER.size)
        if hdr is None:
            break
        magic, w, h, _ = HEADER.unpack(hdr)
        if magic != SYNC or w != W or h != H:
            buf = buf[1:]            # 失步：丢 1 字节重新找帧头
            continue
        payload, buf = read_exact(ser, buf, NBYTES)
        if payload is None:
            break
        frame = np.frombuffer(payload, dtype=np.uint8).reshape(H, W)
        n += 1
        if t0 is None:
            t0 = time.time()
        if prev is not None:
            # 帧差平均幅度 = 朴素运动能量（正式接 ME CUDA 模块时替换这一行）
            me = float(np.mean(np.abs(frame.astype(np.int16) - prev.astype(np.int16))))
            fps = n / (time.time() - t0)
            print("frame %5d  fps=%.1f  motion_energy=%.2f" % (n, fps, me), end="\r")
        prev = frame
except KeyboardInterrupt:
    pass

print("\nstopped: %d frames in %.1fs" % (n, time.time() - t0 if t0 else 0))
