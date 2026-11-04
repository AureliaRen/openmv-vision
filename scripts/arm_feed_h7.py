# 机械臂位置采集 (H7/H7 Plus) —— 检测目标色块，USB 虚拟串口输出位置，供电脑端机械臂程序读取
import sensor
import time

FRAME_SIZE = sensor.QVGA
GREEN_THRESHOLD = (19, 100, -66, -19, 14, 64)
PIXELS_THRESHOLD = 300
AREA_THRESHOLD = 300
DETECTION_ROI = None

WHITE = (255, 255, 255)
RED = (255, 0, 0)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(FRAME_SIZE)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
clock = time.clock()

seq = 0
while True:
    clock.tick()
    img = sensor.snapshot()
    w = img.width()
    h = img.height()
    cx0 = w // 2
    cy0 = h // 2
    ux = w / 2.0
    uy = h / 2.0

    arguments = {
        "pixels_threshold": PIXELS_THRESHOLD,
        "area_threshold": AREA_THRESHOLD,
        "merge": True,
        "margin": 5,
    }
    if DETECTION_ROI is not None:
        arguments["roi"] = DETECTION_ROI
    blobs = img.find_blobs([GREEN_THRESHOLD], **arguments)

    if blobs:
        b = max(blobs, key=lambda i: i.pixels() * 4 + i.pixels() * 1000 // max(1, i.w() * i.h()))
        cx, cy = b.cx(), b.cy()
        nx = (cx - cx0) / ux
        ny = (cy0 - cy) / uy
        img.draw_rectangle(b.rect(), color=WHITE)
        img.draw_cross(cx, cy, color=WHITE)
        img.draw_string(2, 2, "(%+.2f,%+.2f)" % (nx, ny), color=WHITE, mono_space=False)
        print("P,%d,%d,%d,%.3f,%.3f,%d,%d" % (seq, cx, cy, nx, ny, b.w(), b.pixels()))
    else:
        img.draw_string(2, 2, "LOST", color=RED, mono_space=False)
        print("L,%d" % seq)
    seq = (seq + 1) & 0x7FFFFFFF
