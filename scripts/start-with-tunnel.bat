@echo off
REM Запускает PaintGuide и открывает публичный адрес в интернете.
REM Два окна: первое — сервер, второе — туннель со ссылкой.
setlocal

cd /d "%~dp0.."

echo.
echo   PaintGuide: запуск сервера и публичного туннеля
echo   Ссылка появится во втором окне. Не закрывайте его.
echo.

start "PaintGuide server" cmd /k "python run.py"
timeout /t 4 /nobreak >nul
start "PaintGuide tunnel" cmd /k "python scripts\tunnel.py"

endlocal
