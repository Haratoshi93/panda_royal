@echo off
chcp 65001 > nul

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Running setup_and_run.bat...
    call setup_and_run.bat
    exit /b
)

call .venv\Scripts\activate.bat
echo Starting Streamlit app...
streamlit run app.py

pause
