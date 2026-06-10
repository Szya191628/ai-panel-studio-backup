@echo off
echo Starting AI Panel Studio Backend...
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pause
