# 运动状态估计 (H7/H7 Plus) —— 色块检测 + 速度/方向/状态判定
import sensor
import image
import time
import math

green_threshold = (0, 80, -70, -10, -0, 30)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
clock = time.clock()

prev_x = None          # 上一帧坐标与时间
prev_y = None
prev_t = None
vx_s = 0.0             # EMA 平滑后的速度 (px/s)
vy_s = 0.0
moving = False         # 滞回状态锁存：当前是否判定为运动
ALPHA = 0.2            # 平滑系数：越小越稳、反应越迟钝
V_ENTER = 130.0        # STOP→MOVE 需要超过 130（严格）
V_EXIT = 70.0         # MOVE→STOP 需要低于 70（宽松）
while(True):
    clock.tick()
    img = sensor.snapshot()
    blobs = img.find_blobs([green_threshold],
                           pixels_threshold=50,  # 空间域降噪：小碎块过滤
                           area_threshold=50,
                           merge=True,
                           margin=10)
    if not blobs:
        prev_x = prev_y = prev_t = None   # 丢目标就重置，防止跨帧乱差分
        moving = False                    # 状态也归零，重新出现从 STOP 起判
        continue

    b = max(blobs, key=lambda i: i[4])    # 取像素数最多的色块
    cx, cy = b[5], b[6]
    t = time.ticks_ms()

    if prev_x is not None:
        dt = time.ticks_diff(t, prev_t) / 1000.0    # 换算成秒
        if dt > 0:
            vx = (cx - prev_x) / dt
            vy = (cy - prev_y) / dt
            vx_s = ALPHA * vx + (1 - ALPHA) * vx_s
            vy_s = ALPHA * vy + (1 - ALPHA) * vy_s
            speed = math.sqrt(vx_s * vx_s + vy_s * vy_s)
            # 滞回判决：进 MOVE 用严格阈值，退 STOP 用宽松阈值
            if moving:
                moving = speed >= V_EXIT
            else:
                moving = speed > V_ENTER
            if moving:
                ang = math.degrees(math.atan2(-vy_s, vx_s))  # y取负=数学方向角
                state = "MOVE %ddeg" % int(ang)
            else:
                state = "STOP"
            print("x=%d y=%d v=%.1f px/s %s fps=%.0f" % (cx, cy, speed, state, clock.fps()))

    prev_x, prev_y, prev_t = cx, cy, t
