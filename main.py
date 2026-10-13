import io
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, llm, rag

app = FastAPI(title="Padhai Saathi")
db.init()

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

TUTOR = (
    "Tum 'Padhai Saathi' ho, ek dost jaisa study tutor. Student ki bhasha mein jawab do: "
    "agar wo Hinglish/Hindi mein pooche toh Hinglish (Roman script) mein, English mein pooche toh English mein. "
    "Simple bhasha, chhote examples, aur zarurat ho toh step-by-step. "
    "Neeche diye gaye NOTES ke basis par jawab do. Agar notes mein jawab nahi hai, saaf bolo ki notes mein nahi mila, "
    "phir apne general knowledge se madad karo aur ye bhi batao ki wo notes se bahar ka hai."
)


def wrap(fn):
    try:
        return fn()
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa
        raise HTTPException(500, f"Kuch gadbad hui: {e}")


@app.get("/api/docs")
def list_docs():
    with db.conn() as c:
        rows = c.execute(
            "SELECT d.id, d.name, COUNT(k.id) AS chunks FROM docs d LEFT JOIN chunks k ON k.doc_id=d.id GROUP BY d.id ORDER BY d.id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    raw = await file.read()
    name = file.filename or "notes"
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    else:
        text = raw.decode("utf-8", errors="ignore")
    if len(text.strip()) < 50:
        raise HTTPException(400, "File se text nahi nikla. Scanned PDF hai toh pehle OCR karna padega.")
    doc_id = rag.save_doc(name, text)
    return {"id": doc_id, "name": name, "chars": len(text)}


@app.delete("/api/docs/{doc_id}")
def delete_doc(doc_id: int):
    with db.conn() as c:
        c.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        c.execute("DELETE FROM attempts WHERE doc_id=?", (doc_id,))
        c.execute("DELETE FROM docs WHERE id=?", (doc_id,))
    return {"ok": True}


class Msg(BaseModel):
    role: str
    content: str


class ChatReq(BaseModel):
    message: str
    history: List[Msg] = []
    doc_ids: Optional[List[int]] = None


@app.post("/api/chat")
def chat(req: ChatReq):
    hits = rag.search(req.message, req.doc_ids, k=5)
    notes = "\n\n".join(f"[{h['name']}] {h['text']}" for h in hits) or "(koi notes upload nahi hue)"
    msgs = [{"role": m.role, "content": m.content} for m in req.history[-8:]]
    msgs.append({"role": "user", "content": req.message})
    answer = wrap(lambda: llm.ask(f"{TUTOR}\n\nNOTES:\n{notes}", msgs))
    return {"answer": answer, "sources": sorted({h["name"] for h in hits})}


class GenReq(BaseModel):
    doc_ids: Optional[List[int]] = None
    count: int = 5
    topic: Optional[str] = None


def _context(req: GenReq):
    ctx = rag.search(req.topic, req.doc_ids, k=6) if req.topic else None
    text = "\n\n".join(h["text"] for h in ctx) if ctx else rag.sample_context(req.doc_ids)
    if not text:
        raise HTTPException(400, "Pehle koi notes upload karo.")
    return text


@app.post("/api/quiz")
def quiz(req: GenReq):
    text = _context(req)
    n = max(1, min(req.count, 15))
    prompt = (
        f"Neeche notes hain. Inse {n} multiple-choice questions banao (Hinglish mein, 4 options). "
        'Format: [{"question": str, "options": [str,str,str,str], "answer": int (0-3), '
        '"explanation": str (chhota, Hinglish), "topic": str (2-4 words)}]\n\nNOTES:\n' + text
    )
    return wrap(lambda: llm.ask_json("Tum ek exam question setter ho.", prompt))


@app.post("/api/flashcards")
def flashcards(req: GenReq):
    text = _context(req)
    n = max(1, min(req.count, 20))
    prompt = (
        f"Notes se {n} flashcards banao (Hinglish). Format: "
        '[{"front": str (sawal ya term), "back": str (chhota jawab), "topic": str}]\n\nNOTES:\n' + text
    )
    return wrap(lambda: llm.ask_json("Tum ek revision coach ho.", prompt))


class AttemptReq(BaseModel):
    doc_id: Optional[int] = None
    topic: str
    correct: bool


@app.post("/api/attempt")
def attempt(req: AttemptReq):
    with db.conn() as c:
        c.execute("INSERT INTO attempts(doc_id, topic, correct) VALUES (?,?,?)", (req.doc_id, req.topic, int(req.correct)))
    return {"ok": True}


@app.get("/api/progress")
def progress():
    with db.conn() as c:
        rows = c.execute(
            "SELECT topic, COUNT(*) AS total, SUM(correct) AS right FROM attempts GROUP BY topic ORDER BY (1.0*SUM(correct)/COUNT(*)) ASC"
        ).fetchall()
    out = [{"topic": r["topic"], "total": r["total"], "right": r["right"], "pct": round(100 * r["right"] / r["total"])} for r in rows]
    return {"topics": out, "weak": [t["topic"] for t in out if t["pct"] < 60]}


class PlanReq(BaseModel):
    days_left: int
    hours_per_day: float = 2
    doc_ids: Optional[List[int]] = None


@app.post("/api/plan")
def plan(req: PlanReq):
    weak = progress()["weak"]
    sample = rag.sample_context(req.doc_ids, 5000)
    prompt = (
        f"Exam mein {req.days_left} din bache hain, roz {req.hours_per_day} ghante padhne ka time hai.\n"
        f"Weak topics: {', '.join(weak) or 'abhi koi data nahi'}.\n"
        "Notes ke basis par ek din-ba-din revision plan banao (Hinglish, markdown list). "
        "Weak topics ko zyada time do, aakhri din full revision aur self-test rakho.\n\nNOTES:\n" + sample
    )
    answer = wrap(lambda: llm.ask("Tum ek study planner ho.", [{"role": "user", "content": prompt}], 2000))
    return {"plan": answer, "weak": weak}


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
