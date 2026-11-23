@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title 3D Gaussian Splatting Web Studio

echo ========================================================
echo   🚀 KHỞI ĐỘNG 3D GAUSSIAN SPLATTING WEB STUDIO (RTX 4050)
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [LỖI] Không tìm thấy môi trường ảo .venv!
    pause
    exit /b 1
)

echo [*] Đang kích hoạt môi trường Python .venv...
call .venv\Scripts\activate.bat

echo [*] Đang mở trình duyệt web...
start "" http://localhost:7860

echo [*] Đang khởi chạy máy chủ Web UI tại http://localhost:7860...
echo.
python web_ui.py

pause
