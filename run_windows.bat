@echo off
title CampusMitra - RAG University Chatbot
cd /d "%~dp0"
if not exist ".venv" (
  echo Creating Python virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 py -3 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist ".env" copy ".env.example" ".env"
echo.
echo Starting CampusMitra...
python app.py
pause
