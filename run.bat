@echo off
if not exist venv python -m venv venv
call venv\Scripts\activate
pip install -q -r requirements.txt
if not exist .env (
  copy .env.example .env
  echo .env bana diya. Usme ANTHROPIC_API_KEY daalo aur dobara run.bat chalao.
  exit /b 1
)
uvicorn backend.main:app --reload --port 8000
