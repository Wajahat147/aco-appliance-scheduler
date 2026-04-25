@echo off
echo.
echo ============================================================
echo   ACO Appliance Scheduler - starting local demo server
echo ============================================================
echo.
python -m pip install -q -r requirements.txt
echo.
echo Server starting... your browser will open in 3 seconds.
echo Press Ctrl+C in this window to stop the server.
echo.
start "" http://127.0.0.1:5000
python app.py
