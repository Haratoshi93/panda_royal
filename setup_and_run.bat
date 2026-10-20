@echo off
chcp 65001 > nul

echo Starting Panda Royal Tournament Manager setup...

if not exist ".venv" (
    echo Creating virtual environment...
    py -3.12 -m venv .venv 2>nul
    if errorlevel 1 (
        echo Fallback to default py launcher...
        py -m venv .venv
    )
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Checking and installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Launching Streamlit App...
streamlit run app.py

pause
