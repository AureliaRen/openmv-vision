# AprilTag 3D 定位 (H7/H7 Plus) —— 输出 6 自由度：Tx Ty Tz + Rx Ry Rz
import sensor
import image
import time
import math

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)
sensor.skip_frames(time=2000)
sensor.set_auto_gain(False)
sensor.set_auto_whitebal(False)
clock = time.clock()

# 相机内参：焦距换算成"像素单位"
# 注意！教程里 3.984/2.952 是 OV7725(M7) 的感光尺寸；
# 你的 H7 Plus 是 OV5640，感光面约 3.674 x 2.738 mm，数值要换成下面这组。
# 这是粗略默认值，要精确测距还需实测标定。
# 内参在主循环里按当前分辨率动态计算（以后换分辨率也不用改代码）

def degrees(radians):
    return (180 * radians) / math.pi

while(True):
    clock.tick()
    img = sensor.snapshot()
    f_x = (2.8 / 3.674) * img.width()   # OV5640 感光宽 3.674mm
    f_y = (2.8 / 2.738) * img.height()  # OV5640 感光高 2.738mm
    c_x = img.width() * 0.5
    c_y = img.height() * 0.5
    for tag in img.find_apriltags(fx=f_x, fy=f_y, cx=c_x, cy=c_y):
        img.draw_rectangle(tag.rect, color=(255, 0, 0))
        img.draw_cross(tag.cx, tag.cy, color=(0, 255, 0))
        print_args = (tag.x_translation, tag.y_translation,
                      tag.z_translation,
                      degrees(tag.x_rotation), degrees(tag.y_rotation),
                      degrees(tag.z_rotation))
        # 位置 Tx/Ty/Tz 是相对单位（与tag尺寸相关），需标定换算；旋转单位是度
        print("Tx:%.2f Ty:%.2f Tz:%.2f Rx:%.1f Ry:%.1f Rz:%.1f" % print_args)
    print(clock.fps())
