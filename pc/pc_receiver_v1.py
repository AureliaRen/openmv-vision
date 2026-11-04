# pc_receiver_v1.py —— 电脑端：解析 V1 文本包的接收器（黄色目标追踪）
# 数据源：板上固件经 USB 虚拟串口每帧打印一行 V1 包
# 协议格式：V1,seq,state,err‰,cx,cy,pixels,center_frames,reached
# 格式: V1,seq,state,error_milli,cx,cy,pixels,center_frames,reached
#       state: -1=LEFT  0=CENTER  1=RIGHT  2=LOST
# 用法: python pc_receiver_v1.py COM4    (Ctrl+C 停止)
# 依赖: pip install pyserial
import sys
import time
import serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM4"
STATE_NAME = {"-1": "LEFT", "0": "CENTER", "1": "RIGHT", "2": "LOST"}

ser = serial.Serial(port, 115200, timeout=1.0)   # USB CDC 忽略波特率
print("listening on", port, "... (Ctrl+C to stop)")

n = 0
bad = 0
t0 = None
try:
    while True:
        raw = ser.readline()                     # 读一行（到 \n）
        line = raw.decode("ascii", "ignore").strip()
        if not line.startswith("V1,"):
            if line:
                bad += 1
            continue
        fields = line.split(",")
        if len(fields) != 9:
            bad += 1
            continue
        try:
            seq = int(fields[1])
            state = int(fields[2])
            err = int(fields[3])
            cx = int(fields[4])
            cy = int(fields[5])
            pix = int(fields[6])
            reached = int(fields[8])
        except ValueError:
            bad += 1
            continue
        n += 1
        if t0 is None:
            t0 = time.time()
        fps = n / (time.time() - t0)
        print("seq=%-8d state=%-6s err=%+5d cx=%4d cy=%4d px=%6d reached=%d fps=%.1f"
              % (seq, STATE_NAME.get(str(state), "?"), err, cx, cy, pix,
                 reached, fps), end="\r")
        # ★ ME CUDA 接入点：这里的 (time, err, cx, cy) 流就是电脑端拿到的数据，
        #   确认 ME 输入格式后在本循环里调用真模块即可
except KeyboardInterrupt:
    pass

print("\nstopped: %d packets (%d malformed)" % (n, bad))
