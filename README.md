# Padhai Saathi: AI Study Buddy (Hinglish)

Apne notes ya PDF upload karo. Phir:
- **Doubt poocho**: Hinglish mein chat, jawab tumhare notes se (RAG), voice input ke saath
- **Quiz**: notes se MCQ, explanation ke saath
- **Flashcards**: flip karke revise karo
- **Progress aur plan**: weak topics track hote hain, aur exam ke hisaab se revision plan banta hai

## Chalane ka tarika

Python 3.10+ chahiye.

```bash
./run.sh        # Mac/Linux
run.bat         # Windows
```

Pehli baar `.env` ban jayega. Usme `ANTHROPIC_API_KEY` daalo (console.anthropic.com se milti hai) aur dobara run karo.
Phir browser mein kholo: http://localhost:8000

Voice button Chrome/Edge mein chalta hai.

## Folder structure

```
backend/
  main.py   API routes (upload, chat, quiz, flashcards, progress, plan)
  rag.py    chunking + BM25 search
  llm.py    Claude API wrapper
  db.py     SQLite (docs, chunks, attempts)
frontend/   index.html, style.css, app.js (koi build step nahi)
tests/      basic RAG test
```

## Aage kya add karein

1. **Better RAG**: `rag.py` mein BM25 ki jagah ChromaDB + embeddings (interface `search()` wahi rakho)
2. **Login**: har student ka alag data (users table + JWT)
3. **Streaming answers**: chat ko token-by-token dikhao
4. **Quiz battle**: WebSocket se dost ke saath
5. **Telegram bot**: `python-telegram-bot` se same backend call karo
6. **Deploy**: Render ya Railway par (start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`)

## Dhyan rakhne wali baat

- Scanned PDF (sirf images) se text nahi nikalta; pehle OCR karo
- Abhi sab users ka data ek hi database mein hai (single-user app); deploy karne se pehle login lagao
