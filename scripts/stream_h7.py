# 实时推流 (H7/H7 Plus) —— USB 把灰度帧推给电脑，电脑端跑 pc_receiver.py 计算
# 用法：本脚本用 IDE 的"将打开的脚本保存到 OpenMV Cam（作为 main.py）"烧进去
#       → 拔插一次 USB（或断开 IDE）→ 相机独立运行开始推流
#       → 电脑上：python pc_receiver.py COM4
import sensor
import time
import pyb
import struct

HDR = b"\xAA\x55"       # 帧头同步字
TARGET_MS = 33          # 目标约 30fps（USB 实测带宽 ~0.6~1MB/s，贪快会堵）

sensor.reset()
sensor.set_pixformat(sensor.GRAYSCALE)   # 灰度：带宽减半，运动能量本来只吃亮度
sensor.set_framesize(sensor.QQVGA)       # 160x120 = 19200字节/帧
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

vcp = pyb.USB_VCP()
clock = time.clock()
last = time.ticks_ms()

while(True):
    img = sensor.snapshot()
    now = time.ticks_ms()
    if time.ticks_diff(now, last) < TARGET_MS:
        continue
    last = now
    payload = bytes(img)                          # 图像缓冲区直接转字节
    vcp.write(struct.pack("<2sHHB", HDR, 160, 120, 0))   # 7字节帧头
    vcp.write(payload)
    clock.tick()
    # 注：板上 fps 只代表拍摄节奏，真实到达率以电脑端打印为准
