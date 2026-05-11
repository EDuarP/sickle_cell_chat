"""
Pipeline de indexación:

  scrape PMC  ->  Documents  ->  chunks  ->  embeddings  ->  Chroma

Uso directo (CLI):
    python -m rag.build_index

También se expone `build_index_stream()` para que la API pueda
emitir progreso por SSE al frontend.
"""
import logging
from typing import Iterator

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from config import (
    QUERIES, PMC_RETMAX, PMC_MINDATE, PMC_MAXDATE,
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, PERSIST_DIR,
)
from scrapers.pmc_scraper import search_pmc, fetch_pmc_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("build_index")


def index_is_ready() -> bool:
    """Heurística rápida: existe el dir y contiene la SQLite de Chroma."""
    if not PERSIST_DIR.exists():
        return False
    return (PERSIST_DIR / "chroma.sqlite3").exists()


def _articles_to_docs(articles: list[dict]) -> list[Document]:
    docs: list[Document] = []
    for art in articles:
        if not (art["abstract"] or art["body"]):
            continue
        content = (
            f"# {art['title']} ({art['year']})\n\n"
            f"## Abstract\n{art['abstract']}\n\n"
            f"## Body\n{art['body']}"
        )
        docs.append(Document(
            page_content=content,
            metadata={
                "source": art["url"],
                "id": art["id"],
                "type": "pmc",
                "year": art["year"],
                "title": art["title"][:200],
            },
        ))
    return docs


def build_index_stream() -> Iterator[dict]:
    """
    Generador que emite el progreso de cada etapa.
    Cada `yield` es un dict {stage, message, [progress]}.
    """
    yield {"stage": "search", "message": f"Buscando en PMC ({len(QUERIES)} queries)…"}
    seen: set[str] = set()
    pmcids: list[str] = []
    for q in QUERIES:
        for pid in search_pmc(q, retmax=PMC_RETMAX, mindate=PMC_MINDATE, maxdate=PMC_MAXDATE):
            if pid not in seen:
                seen.add(pid)
                pmcids.append(pid)
    yield {"stage": "search", "message": f"{len(pmcids)} PMCIDs únicos"}

    if not pmcids:
        yield {"stage": "error", "message": "No se encontraron artículos en PMC"}
        return

    yield {"stage": "fetch", "message": f"Descargando {len(pmcids)} artículos de PMC…"}
    articles = fetch_pmc_articles(pmcids)
    docs = _articles_to_docs(articles)
    yield {"stage": "fetch", "message": f"{len(docs)} documentos con contenido útil"}

    if not docs:
        yield {"stage": "error", "message": "Ningún artículo trajo contenido aprovechable"}
        return

    yield {"stage": "split", "message": "Troceando documentos…"}
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    yield {"stage": "split", "message": f"{len(docs)} docs → {len(chunks)} chunks"}

    yield {"stage": "embed", "message": f"Cargando embeddings ({EMBEDDING_MODEL}) — primera vez descarga ~90 MB"}
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    yield {"stage": "index", "message": f"Indexando {len(chunks)} chunks en Chroma…"}
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    yield {"stage": "done", "message": f"Índice listo en {PERSIST_DIR.name}/"}


def main() -> None:
    for ev in build_index_stream():
        log.info(f"[{ev['stage']}] {ev['message']}")
        if ev["stage"] == "error":
            return
    log.info("Siguiente paso: python -m rag.chatbot")


if __name__ == "__main__":
    main()
