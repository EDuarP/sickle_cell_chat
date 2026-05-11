"""
HTTP API del chatbot RAG. Sirve también el frontend estático.

    uvicorn api.server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import OLLAMA_MODEL, OLLAMA_API_KEY, PMC_MINDATE, PMC_MAXDATE
from rag.build_index import build_index_stream, index_is_ready
from rag.chatbot import build_chain

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Sickle Cell RAG")

_chain = None
_chain_lock = threading.Lock()
_init_lock = threading.Lock()


def get_chain():
    global _chain
    with _chain_lock:
        if _chain is None:
            log.info("Cargando chain RAG…")
            _chain = build_chain()
        return _chain


def reset_chain():
    global _chain
    with _chain_lock:
        _chain = None


class ChatRequest(BaseModel):
    question: str


@app.get("/api/status")
def status():
    return {
        "ready": index_is_ready(),
        "model": OLLAMA_MODEL,
        "has_api_key": bool(OLLAMA_API_KEY),
        "indexing": _init_lock.locked(),
        "date_min": PMC_MINDATE,
        "date_max": PMC_MAXDATE,
    }


@app.post("/api/init")
def init():
    if not _init_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="indexing already in progress")

    def gen():
        try:
            for ev in build_index_stream():
                yield f"data: {json.dumps(ev)}\n\n"
                if ev.get("stage") == "error":
                    return
            reset_chain()
        except Exception as e:
            log.exception("error durante init")
            yield f"data: {json.dumps({'stage': 'error', 'message': str(e)})}\n\n"
        finally:
            _init_lock.release()
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat")
def chat(req: ChatRequest):
    q = (req.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="empty question")
    if not index_is_ready():
        raise HTTPException(status_code=503, detail="index not ready — call /api/init first")

    try:
        chain = get_chain()
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    def gen():
        try:
            for chunk in chain.stream(q):
                if not chunk:
                    continue
                yield f"data: {json.dumps({'token': chunk})}\n\n"
        except Exception as e:
            log.exception("error durante stream")
            yield f"data: {json.dumps({'error': _friendly_error(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _friendly_error(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "nodename nor servname" in low or "name or service not known" in low \
       or "getaddrinfo" in low or "connecterror" in low:
        return ("No se pudo resolver ollama.com. Revisa la conexión a Internet. "
                "En macOS prueba: sudo dscacheutil -flushcache; "
                "sudo killall -HUP mDNSResponder")
    if "401" in msg or "unauthorized" in low:
        return "OLLAMA_API_KEY inválida o expirada. Revísala en https://ollama.com/settings/keys"
    if "timeout" in low or "timed out" in low:
        return "Timeout conectando al LLM. Reintenta en unos segundos."
    return msg


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
