# Hello World Example (H7/H7 Plus)
import sensor
import image
import time

sensor.reset()                      # 复位并初始化摄像头
sensor.set_pixformat(sensor.RGB565) # 设置为彩色
sensor.set_framesize(sensor.QVGA)   # 320x240
sensor.skip_frames(time=2000)       # 等待设置生效
clock = time.clock()                # 帧率时钟

while(True):
    clock.tick()
    img = sensor.snapshot()         # 拍一帧并返回图像
    print(clock.fps())              # 打印帧率
