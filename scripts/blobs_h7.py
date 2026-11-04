# 色块监测·多颜色版 (H7/H7 Plus) —— 多阈值检测 + 按颜色编号(code)选目标
# code 规则：1=1号阈值(绿)，2=2号阈值(橙占位)，3=两个阈值都命中(位掩码)
import sensor
import image
import time

# ---- 阈值区：换光照/换目标就在 IDE 阈值编辑器里重标 ----
green_threshold  = (0, 80, -70, -10, -0, 30)    # 1号：绿（已实测可用）
orange_threshold = (0, 80, 10, 60, 40, 100)     # 2号：橙【占位示例值，未标定，现场用阈值编辑器重取！】

TARGET_CODE = 1        # 要追的颜色：1=绿 2=橙 3=两种都追，改这一个数就切目标

# 各编号对应的画框颜色（肉眼区分用）
BOX_COLOR = {1: (0, 255, 0), 2: (255, 128, 0), 3: (255, 255, 255)}

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)  # 160x120，分辨率小跑得快
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)         # 颜色识别必须关自动增益
sensor.set_auto_whitebal(False)     # 必须关自动白平衡
clock = time.clock()

while(True):
    clock.tick()
    img = sensor.snapshot()
    blobs = img.find_blobs([green_threshold, orange_threshold],
                           pixels_threshold=50,  # 噪声过滤①：不足50像素的扔掉
                           area_threshold=50,    # 噪声过滤②：外接框太小的扔掉
                           merge=True,           # 噪声过滤③：相邻碎块合并
                           margin=10)            #   "相邻"判定距离(像素)
    # ---- 按颜色编号选目标（多颜色区分的关键一行）----
    targets = [b for b in blobs if b.code() == TARGET_CODE]

    for b in targets:
        c = BOX_COLOR.get(b.code(), (255, 255, 255))
        img.draw_rectangle(b.rect(), color=c)    # 框出色块（框色随编号变）
        img.draw_cross(b.cx(), b.cy(), color=c)  # 标记中心 (cx, cy)
        print("code=%d cx=%d cy=%d px=%d" % (b.code(), b.cx(), b.cy(), b.pixels()))
    print(clock.fps())
