# AprilTag 2D 检测 (H7/H7 Plus) —— 识别 id + 中心 + 旋转角
import sensor
import image
import time
import math

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)   # AprilTag 吃内存，QQVGA 起步
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)          # 必须关，否则图像过曝
sensor.set_auto_whitebal(False)
clock = time.clock()

while(True):
    clock.tick()
    img = sensor.snapshot()
    # 默认就是 TAG36H11 家族
    for tag in img.find_apriltags():
        img.draw_rectangle(tag.rect, color=(255, 0, 0))
        img.draw_cross(tag.cx, tag.cy, color=(0, 255, 0))
        print_args = (tag.id, tag.cx, tag.cy,
                      180 * tag.rotation / math.pi)
        print("id=%d cx=%d cy=%d rot=%.1fdeg" % print_args)
    print(clock.fps())
