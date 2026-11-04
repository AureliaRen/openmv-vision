@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
cl /nologo /std:c++17 /EHsc /O2 /utf-8 ^
  /I "D:\dev\zeromq\zeromq-4.3.5\include" ^
  /I "D:\dev\zeromq" ^
  v1_to_spikes_bridge.cpp ^
  /link "D:\dev\zeromq\build\lib\Release\libzmq-v145-mt-4_3_5.lib" ^
  ws2_32.lib iphlpapi.lib advapi32.lib
if errorlevel 1 exit /b 1
copy /y "D:\dev\zeromq\build\bin\Release\libzmq-v145-mt-4_3_5.dll" "%~dp0" >nul
echo build ok
