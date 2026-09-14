@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在启动 GRE Vocabulary System...
echo 本地地址：http://127.0.0.1:8501
echo.

if not exist ".venv\Scripts\python.exe" (
    echo 未找到 .venv\Scripts\python.exe，请确认虚拟环境仍在本项目目录中。
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501

echo.
echo 网站进程已结束。若不是你主动关闭，请把上面的报错发给我。
pause
