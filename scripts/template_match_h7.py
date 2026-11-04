# NCC 模板匹配 (H7/H7 Plus)
# 前提：先把 template.pgm 拷到 OpenMV U 盘的根目录，再运行本脚本
import sensor
import image
import time
from image import SEARCH_EX, SEARCH_DS

sensor.reset()
sensor.set_contrast(1)                  # 提高对比度，NCC 更稳
sensor.set_gainceiling(16)
sensor.set_framesize(sensor.QQVGA)      # SEARCH_EX 最高支持 QQVGA
sensor.set_pixformat(sensor.GRAYSCALE)  # NCC 只支持灰度图
sensor.skip_frames(time=2000)

template = image.Image("/template.pgm")  # 模板路径：U盘根目录
clock = time.clock()

while(True):
    clock.tick()
    img = sensor.snapshot()
    # find_template(模板, 相似度阈值0.70, step=采样步长, search=搜索策略)
    # SEARCH_EX=穷举搜索(准)，SEARCH_DS=菱形搜索(快)；阈值越低越"宽容"
    r = img.find_template(template, 0.70, step=4, search=SEARCH_EX)
    if r:
        img.draw_rectangle(r)
    print(clock.fps())
