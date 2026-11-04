# 色块+运动+区域判决：左=-1 中=0 右=1，丢失=LOST
import sensor
import time
import math

FRAME_SIZE = sensor.QVGA
GREEN_THRESHOLD = (19, 100, -66, -19, 14, 64)
PIXELS_THRESHOLD = 300
AREA_THRESHOLD = 300
DETECTION_ROI = None

ALPHA = 0.4
HIST_N = 12
D_ENTER = 20.0
D_EXIT = 10.0
Z_ENTER = 16.0

ERR_ALPHA = 0.35
CENTER_ENTER = 0.05
CENTER_EXIT = 0.08
SIDE_CONFIRM = 2

ZONE_EN = {-1: "LEFT", 0: "CENTER", 1: "RIGHT", 2: "LOST"}

GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(FRAME_SIZE)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
clock = time.clock()

prev_x = prev_y = prev_t = None
prev_w = None
vx_s = vy_s = 0.0
w_s = 0.0
hist_x = []
hist_y = []
moving = False
zone = 2
candidate = 2
candidate_frames = 0
err_s = 0.0
has_err = False

while True:
    clock.tick()
    img = sensor.snapshot()
    w = img.width()
    h = img.height()
    cx0 = w // 2
    cy0 = h // 2
    ux = w / 2.0
    uy = h / 2.0

    img.draw_line(0, cy0, w - 1, cy0, color=GRAY)
    img.draw_line(cx0, 0, cx0, h - 1, color=GRAY)
    for i in range(-2, 3):
        px = int(cx0 + i * ux / 2)
        img.draw_line(px, cy0 - 3, px, cy0 + 3, color=GRAY)
    img.draw_string(2, cy0 + 4, "-1", color=YELLOW, scale=1)
    img.draw_string(cx0 + 4, cy0 + 4, "0", color=YELLOW, scale=1)
    img.draw_string(w - 12, cy0 + 4, "1", color=YELLOW, scale=1)
    for i in range(-2, 3):
        py = int(cy0 - i * uy / 2)
        img.draw_line(cx0 - 3, py, cx0 + 3, py, color=GRAY)
    img.draw_string(cx0 + 4, 2, "+1", color=YELLOW, scale=1)
    img.draw_string(cx0 + 4, h - 18, "-1", color=YELLOW, scale=1)

    arguments = {
        "pixels_threshold": PIXELS_THRESHOLD,
        "area_threshold": AREA_THRESHOLD,
        "merge": True,
        "margin": 5,
    }
    if DETECTION_ROI is not None:
        arguments["roi"] = DETECTION_ROI
    blobs = img.find_blobs([GREEN_THRESHOLD], **arguments)

    if not blobs:
        zone = candidate = 2
        candidate_frames = 0
        err_s = 0.0
        has_err = False
        prev_x = prev_y = prev_t = None   # 丢目标必须重置，防跨帧差分出瞬移速度
        prev_w = None
        w_s = 0.0
        hist_x = []
        hist_y = []
        moving = False
        img.draw_string(2, 2, ZONE_EN[2], color=RED, mono_space=False)
        print("state=LOST move=-- fps=%.0f" % clock.fps())
        continue

    b = max(blobs, key=lambda i: i.pixels() * 4 + i.pixels() * 1000 // max(1, i.w() * i.h()))
    cx, cy = b.cx(), b.cy()

    t = time.ticks_ms()
    move_txt = "INIT"
    z_txt = "HOLD"
    speed = 0.0
    disp = 0.0
    if prev_x is not None:
        dt = time.ticks_diff(t, prev_t) / 1000.0
        if dt > 0:
            vx = (cx - prev_x) / dt
            vy = (cy - prev_y) / dt
            vx_s = ALPHA * vx + (1 - ALPHA) * vx_s
            vy_s = ALPHA * vy + (1 - ALPHA) * vy_s
            speed = math.sqrt(vx_s * vx_s + vy_s * vy_s)
            if prev_w is not None:
                vw = (b.w() - prev_w) / dt          # 宽度变化率：变大=靠近
                w_s = ALPHA * vw + (1 - ALPHA) * w_s
                if w_s > Z_ENTER:
                    z_txt = "NEAR"
                elif w_s < -Z_ENTER:
                    z_txt = "FAR"
    prev_x, prev_y, prev_t = cx, cy, t
    prev_w = b.w()

    # ---- 运动判决：12帧窗净位移 + 滞回 ----
    # （速度法已证伪：静止尖刺max85 与 慢推60~90 分布重叠；位移法靠零均值噪声窗口内自抵消分离）
    hist_x.append(cx)
    hist_y.append(cy)
    if len(hist_x) > HIST_N:
        hist_x.pop(0)
        hist_y.pop(0)
    if len(hist_x) >= HIST_N:
        disp = math.sqrt((cx - hist_x[0]) ** 2 + (cy - hist_y[0]) ** 2)
        if moving:
            moving = disp >= D_EXIT
        else:
            moving = disp > D_ENTER
        if moving:
            wdx = cx - hist_x[0]
            wdy = cy - hist_y[0]
            ang = math.degrees(math.atan2(-wdy, wdx))
            if abs(wdx) >= abs(wdy):
                dir_txt = "RIGHT" if wdx > 0 else "LEFT"
            else:
                dir_txt = "UP" if wdy < 0 else "DOWN"
            move_txt = "MOVE %s %ddeg" % (dir_txt, int(ang))
        else:
            move_txt = "STOP"

    raw_err = (cx - cx0) / ux
    err_s = raw_err if not has_err else ERR_ALPHA * raw_err + (1 - ERR_ALPHA) * err_s
    has_err = True
    thr = CENTER_EXIT if zone == 0 else CENTER_ENTER   # 滞回：出中央宽门限、进窄门限，防边界抖
    if abs(err_s) <= thr:
        zone = 0
        candidate = 2
        candidate_frames = 0
    else:
        measured = -1 if err_s < 0 else 1
        if measured == candidate:
            candidate_frames += 1
        else:
            candidate = measured
            candidate_frames = 1
        if candidate_frames >= SIDE_CONFIRM:
            zone = measured

    img.draw_rectangle(b.rect(), color=WHITE)
    img.draw_cross(cx, cy, color=WHITE)
    img.draw_string(2, 2, "%s %d %s" % (ZONE_EN[zone], zone, move_txt),
                    color=WHITE, mono_space=False)
    print("state=%d zone=%s move=%s z=%s v=%.1f d=%.1f vw=%+.1f cx=%d cy=%d px=%d fps=%.0f" %
          (zone, ZONE_EN[zone], move_txt, z_txt, speed, disp, w_s, cx, cy, b.pixels(), clock.fps()))
