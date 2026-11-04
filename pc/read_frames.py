# read_frames.py —— 电脑端：读取 OpenMV 拷回的 /log 文件夹，画时间轴+轨迹图
# 用法: python read_frames.py <log文件夹路径>
# 依赖: matplotlib（画图）；缺了先 pip install matplotlib
import sys
import os
import csv
import matplotlib.pyplot as plt

folder = sys.argv[1] if len(sys.argv) > 1 else "log"

ts, xs, ys = [], [], []
with open(os.path.join(folder, "timeline.csv")) as f:
    reader = csv.reader(f)
    next(reader)                       # 跳过表头
    for row in reader:
        ts.append(int(row[1]) / 1000.0)
        xs.append(int(row[2]))
        ys.append(int(row[3]))

found = sum(1 for x in xs if x >= 0)
duration = ts[-1] if ts else 0.0
rate = len(ts) / duration if duration > 0 else 0.0
print("frames=%d (target found in %d)  duration=%.1fs  effective=%.1f fps"
      % (len(ts), found, duration, rate))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
ax1.plot(ts, xs, ".-", label="x (px)")
ax1.plot(ts, ys, ".-", label="y (px)")
ax1.set_xlabel("t (s)")
ax1.set_title("position vs time")
ax1.legend()

pts = [(x, y) for x, y in zip(xs, ys) if x >= 0]
if pts:
    ax2.plot([p[0] for p in pts], [p[1] for p in pts], ".")
ax2.set_xlim(0, 160)
ax2.set_ylim(120, 0)                   # y 向下=图像坐标系方向
ax2.set_aspect("equal")
ax2.set_title("trajectory (image frame)")

plt.tight_layout()
plt.savefig(os.path.join(folder, "trajectory.png"), dpi=150)
print("saved:", os.path.join(folder, "trajectory.png"))
