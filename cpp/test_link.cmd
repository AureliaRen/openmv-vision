@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo  v1_to_spikes 链路自测（无需相机）
echo  1. 启动 C++ 接收端窗口
echo  2. 跑 Python 发送端 loopback
echo  3. 看接收端窗口是否出现 10 批
echo ============================================
echo.

echo [1/2] starting spike_rx_demo.exe ...
start "spike_rx_demo (接收端)" cmd /k "chcp 65001 >nul && spike_rx_demo.exe"
timeout /t 1 /nobreak >nul

echo [2/2] running v1_to_spikes.py --loopback ...
python v1_to_spikes.py --loopback

echo.
echo 测试结束。接收端窗口应显示 10 批（batch#1..10）。
echo 关闭接收端窗口或按 Ctrl+C 停止。
pause >nul
