# 坐标轴可视化 (H7/H7 Plus) —— 画面中心为原点的归一化坐标系 + 色块定位
# 坐标定义：原点=图像中心，x 右正左负（左边缘 -1，右边缘 +1），y 向上为正
import sensor
import image
import time
import math

green_threshold = (0, 80, -70, -10, -0, 30)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)   # 160x120
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
clock = time.clock()

GRAY   = (100, 100, 100)   # 坐标轴与刻度线
YELLOW = (255, 255, 0)     # 刻度数字
BLUE   = (0, 128, 255)     # 目标点与位移矢量

while(True):
    clock.tick()
    img = sensor.snapshot()
    w = img.width()        # 160
    h = img.height()       # 120
    cx0 = w // 2           # 原点像素坐标
    cy0 = h // 2
    ux = w / 2.0           # x 方向 1 个单位 = 半宽 80px
    uy = h / 2.0           # y 方向 1 个单位 = 半高 60px

    # ---- 画坐标轴 ----
    img.draw_line(0, cy0, w - 1, cy0, color=GRAY)
    img.draw_line(cx0, 0, cx0, h - 1, color=GRAY)

    # x 轴刻度：-1, -0.5, 0, +0.5, +1（每 0.5 一格）
    for i in range(-2, 3):
        px = int(cx0 + i * ux / 2)
        img.draw_line(px, cy0 - 3, px, cy0 + 3, color=GRAY)
    img.draw_string(2,       cy0 + 4, "-1", color=YELLOW, scale=1)
    img.draw_string(cx0 + 4, cy0 + 4, "0",  color=YELLOW, scale=1)
    img.draw_string(w - 12,  cy0 + 4, "1",  color=YELLOW, scale=1)

    # y 轴刻度：向上为正
    for i in range(-2, 3):
        py = int(cy0 - i * uy / 2)
        img.draw_line(cx0 - 3, py, cx0 + 3, py, color=GRAY)
    img.draw_string(cx0 + 4, 2,      "+1", color=YELLOW, scale=1)
    img.draw_string(cx0 + 4, h - 18, "-1", color=YELLOW, scale=1)

    # ---- 目标定位（归一化坐标）----
    blobs = img.find_blobs([green_threshold],
                           pixels_threshold=50,  # 空间域降噪：小碎块过滤
                           area_threshold=50,
                           merge=True,
                           margin=10)
    if blobs:
        b = max(blobs, key=lambda i: i[4])
        bx, by = b[5], b[6]
        nx = (bx - cx0) / ux          # [-1, +1]，右正
        ny = (cy0 - by) / uy          # [-1, +1]，上正
        img.draw_arrow(cx0, cy0, bx, by, color=BLUE)      # 位移矢量
        img.draw_circle(bx, by, 4, color=BLUE)
        img.draw_string(bx + 6, by - 8, "(%+.2f,%+.2f)" % (nx, ny),
                        color=BLUE, scale=1)
        print("nx=%+.2f ny=%+.2f fps=%.0f" % (nx, ny, clock.fps()))
    else:
        print("no target fps=%.0f" % clock.fps())
