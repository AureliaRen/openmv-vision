@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cd /d "%~dp0"
cl /nologo /std:c++17 /EHsc /O2 /utf-8 mock_popen_receiver.cpp
if errorlevel 1 exit /b 1
echo build ok
