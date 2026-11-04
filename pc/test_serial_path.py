# -*- coding: utf-8 -*-
"""真机读取路径预演: 用假串口注入测试 SerialLatestSource(无需相机/com0com)
覆盖: 读线程 / parse_v1 过滤 / 最新帧覆盖 / take 语义 / malformed 计数 / close
未覆盖: pyserial 真实打开 COM 口(仅一行)
运行: python test_serial_path.py
"""
import os
import queue
import sys
import threading
import time
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class FakeSerial:
    """模拟 OpenMV 以 1ms 一包的节奏狂发 V1 数据(快于消费端, 触发覆盖)。"""
    def __init__(self, port, baudrate=115200, timeout=0.2):
        self.q = queue.Queue()
        self.closed = False
        self._t = threading.Thread(target=self._produce, daemon=True)
        self._t.start()

    def _produce(self):
        for seq in range(100):
            if seq < 20:
                state = -1
            elif seq < 40:
                state = 0
            elif seq < 60:
                state = 1
            else:
                state = 2
            self.q.put(("V1,%d,%d,%d,80,120,1500,3,0\n" % (seq, state, 100)).encode())
            if seq % 25 == 0:  # 夹在流中间, 确保读线程一定遇到
                self.q.put(b"garbage line\n")
            time.sleep(0.001)  # 1ms/包, 远快于 20ms 消费节拍
        self.q.put(b"garbage line\n")  # 应计入 malformed
        self.closed = True

    def readline(self):
        try:
            return self.q.get(timeout=0.05)
        except queue.Empty:
            return b""

    def close(self):
        self.closed = True


def main():
    fake_mod = types.ModuleType("serial")
    fake_mod.Serial = FakeSerial
    sys.modules["serial"] = fake_mod

    import v1_to_spikes as v

    src = v.SerialLatestSource("COM9")
    print("读线程已启动")

    # 消费者每 20ms 取一次, 与主循环节拍一致
    seen = []
    for _ in range(6):
        time.sleep(0.02)
        pkt = src.take()
        if pkt:
            seen.append((pkt["seq"], pkt["state"]))

    time.sleep(0.15)  # 等读线程把队列剩余部分(含垃圾行)读完
    src.close()
    print("消费到的帧(seq,state):", seen)
    print("frames=%d malformed=%d overwritten=%d" %
          (src.frames, src.malformed, src.overwritten))

    ok = True
    if not seen:
        print("FAIL: 没取到任何帧")
        ok = False
    else:
        # 50ms 后应消费到较新的帧(生产者 100 帧/100ms)
        if seen[-1][0] < 30:
            print("FAIL: 消费帧序号过旧, 覆盖逻辑可疑")
            ok = False
        # 最后取到的最新帧应是 state=2 (seq>=60 之后)
        if seen[-1][1] != 2:
            print("FAIL: 最新帧状态应为 2(LOST), 实际", seen[-1][1])
            ok = False
    if src.malformed < 1:
        print("FAIL: malformed 应>=1, 实际", src.malformed)
        ok = False
    if src.overwritten <= 0:
        print("FAIL: 应有覆盖发生, 实际 overwritten=", src.overwritten)
        ok = False

    print("verdict:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
