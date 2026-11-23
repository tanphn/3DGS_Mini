@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
title Dựng 3DGS Video: room_tour.mp4

echo ========================================================
echo   🚀 DỰNG 3D GAUSSIAN SPLATTING CHO VIDEO: room_tour.mp4
echo   Card: RTX 4050 6GB ^| 7000 steps ^| Tự động nén .splat
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [LỖI] Không tìm thấy môi trường ảo .venv!
    pause
    exit /b 1
)

echo [*] Đang kích hoạt môi trường ảo .venv...
call .venv\Scripts\activate.bat

echo [*] Đang bắt đầu xử lý video_to_3dgs.py...
echo.
python video_to_3dgs.py -v "room_tour.mp4" -s "room_tour" --frames 110 --iterations 7000 -r 2

echo.
echo ========================================================
echo   🎉 HOÀN THÀNH!
echo ========================================================
pause
