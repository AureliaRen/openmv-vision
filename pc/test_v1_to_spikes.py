# -*- coding: utf-8 -*-
"""v1_to_spikes.py 单元测试（不需要相机/串口/ZMQ）
运行: python test_v1_to_spikes.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v1_to_spikes as v


def test_parse_valid():
    p = v.parse_v1("V1,7,-1,850,80,120,1500,3,0")
    assert p["seq"] == 7 and p["state"] == -1 and p["err"] == 850
    p2 = v.parse_v1("V1,0,2,0,0,0,0,0,0")
    assert p2["state"] == 2 and p2["err"] == 0


def test_parse_invalid():
    bad = [
        "", "hello", "V1,1,0,30", "V1,1,0,30,80,120,1500,3",
        "V1,a,0,30,80,120,1500,3,0", "V2,1,0,30,80,120,1500,3,0",
        "DIR,-1",
    ]
    for line in bad:
        assert v.parse_v1(line) is None, "应判非法: %r" % line


def test_encode_lost_silent():
    phase = [0.0]
    assert v.encode_window(2, 0, 0.0, 0.02, phase) == []
    assert phase[0] == 0.0  # LOST 清零相位


def test_encode_phase_accumulator():
    # 20Hz × 20ms = 0.4/窗 → 5 窗 2 个
    phase = [0.0]
    total = sum(len(v.encode_window(0, 0, i * 0.02, 0.02, phase)) for i in range(5))
    assert total == 2, total
    # 100 窗平均速率 = 20Hz ± 1 个
    phase = [0.0]
    total = sum(len(v.encode_window(0, 0, i * 0.02, 0.02, phase)) for i in range(100))
    assert abs(total - 40) <= 1, total


def test_encode_max_rate():
    phase = [0.0]
    s = v.encode_window(1, 1000, 0.0, 0.02, phase)  # 110Hz 上限 × 20ms = 2.2
    assert len(s) == 2, len(s)


def test_encode_timestamps_inside_window():
    phase = [0.0]
    s = v.encode_window(0, 500, 10.0, 0.02, phase)
    assert s, "应有脉冲"
    for neuron, t in s:
        assert neuron == 1
        assert 10.0 <= t < 10.02, t


def test_neurons_mapping():
    for state, nid in [(-1, 0), (0, 1), (1, 2)]:
        phase = [0.0]
        found = []
        for _ in range(3):
            found = v.encode_window(state, 1000, 0.0, 0.02, phase)
            if found:
                break
        assert found and found[0][0] == nid, (state, found)


def test_pack():
    h = v.pack_head(5, 2)
    assert len(h) == 16
    magic, ver, tstep, count = v.HDR.unpack(h)
    assert (magic, ver, tstep, count) == (v.MAGIC, v.VERSION, 5, 2)

    body = v.pack_body([(0, 1.5), (2, 2.5)], 0.0001)
    assert len(body) == 24
    n0, t0, b0 = v.SPIKE.unpack_from(body, 0)
    assert n0 == 0 and abs(t0 - 1.5) < 1e-6 and abs(b0 - 0.0001) < 1e-9
    n1, t1, _ = v.SPIKE.unpack_from(body, 12)
    assert n1 == 2 and abs(t1 - 2.5) < 1e-6


def test_state_domain():
    # V1 状态码只有 -1/0/1/2 合法；编码器对未知状态按 LOST 处理
    phase = [0.0]
    assert v.encode_window(9, 500, 0.0, 0.02, phase) == []
    assert v.encode_window(-5, 500, 0.0, 0.02, phase) == []


def main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except AssertionError as e:
            failed += 1
            print("FAIL", name, "->", e)
    print("\n%d passed, %d failed" % (len(tests) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
