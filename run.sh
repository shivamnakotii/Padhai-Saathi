#!/usr/bin/env bash
set -e
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo ".env bana diya. Usme ANTHROPIC_API_KEY daalo aur dobara run.sh chalao."; exit 1; }
uvicorn backend.main:app --reload --port 8000
