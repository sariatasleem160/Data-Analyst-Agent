@echo off
setlocal
cd /d "%~dp0"

set PY=%~dp0.python-embed\python.exe

if not exist "%PY%" (
    echo ERROR: Python not found. Run setup first.
    pause
    exit /b 1
)

echo Starting Data Analyst Agent on http://localhost:8501
echo Press Ctrl+C to stop.
echo.

"%PY%" -m streamlit run app.py --server.headless true --server.port 8501
