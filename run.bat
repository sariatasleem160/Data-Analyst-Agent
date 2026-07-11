@echo off
cd /d "%~dp0"
echo === Data Analyst Agent ===
echo.
echo 1. Install:  pip install -r requirements.txt
echo 2. Set key:  copy .env.example .env  (edit with your Anthropic key)
echo 3. UI:       streamlit run app.py
echo 4. Eval:     python evaluate.py
echo 5. Tests:    python test_tools.py
echo 6. MCP:      python mcp_server.py
echo.
pause
