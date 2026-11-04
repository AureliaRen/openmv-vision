# 帧序列落盘记录 (H7/H7 Plus) —— 图像+时间戳+坐标存板载U盘，拷回电脑离线分析
# 用法：运行约 10 秒自动结束 → 断开 IDE 连接 → 电脑打开 U 盘把 /log 文件夹拷走
import sensor
import image
import time
import os

green_threshold = (0, 80, -70, -10, -0, 30)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)   # 160x120
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)

# 建日志文件夹（已存在则跳过）
try:
    os.mkdir("/log")
except OSError:
    pass

N_FRAMES  = 200    # 最多存 200 帧（保护 flash，控制文件量）
PERIOD_MS = 50     # 目标每 50ms 一帧（约 20fps；flash 写入慢时以实际为准）
count = 0
t0 = time.ticks_ms()

log = open("/log/timeline.csv", "w")
log.write("frame,t_ms,x,y\n")      # x=y=-1 表示该帧没找到目标
print("recording...")

while count < N_FRAMES:
    img = sensor.snapshot()
    # 按绝对时间表排片：flash 写入慢也不乱节拍
    if time.ticks_diff(time.ticks_ms(), t0) >= count * PERIOD_MS:
        blobs = img.find_blobs([green_threshold])
        x, y = -1, -1
        if blobs:
            b = max(blobs, key=lambda i: i[4])
            x, y = b[5], b[6]
        img.save("/log/f%04d.bmp" % count)
        log.write("%d,%d,%d,%d\n" % (count,
                                     time.ticks_diff(time.ticks_ms(), t0),
                                     x, y))
        count += 1

log.close()
print("done: %d frames in /log, copy it to PC" % count)
