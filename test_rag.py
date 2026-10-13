"""Chalane ke liye: python -m pytest tests  (pip install pytest)"""
from backend import db, rag


def test_search_finds_relevant_chunk(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db.init()
    text = ("Photosynthesis mein paudhe sunlight se khana banate hain. " * 8 +
            "Newton ka doosra niyam kehta hai force barabar mass guna acceleration. " * 8)
    rag.save_doc("sci.txt", text)
    hits = rag.search("Newton ka niyam kya hai", k=1)
    assert hits and "Newton" in hits[0]["text"]
