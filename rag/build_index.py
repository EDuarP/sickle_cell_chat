"""
Pipeline de indexación:

  scrape PMC  ->  Documents  ->  chunks  ->  embeddings  ->  Chroma

Correr una sola vez (o cuando quieras refrescar datos):
    python -m rag.build_index
"""
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from config import (
    QUERY, PMC_RETMAX, PMC_MINDATE, PMC_MAXDATE,
    CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL, PERSIST_DIR,
)
from scrapers.pmc_scraper import search_pmc, fetch_pmc_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("build_index")


def build_documents() -> list[Document]:
    docs: list[Document] = []

    # --- PMC (E-utilities) ---
    pmcids = search_pmc(QUERY, retmax=PMC_RETMAX, mindate=PMC_MINDATE, maxdate=PMC_MAXDATE)
    articles = fetch_pmc_articles(pmcids)

    n_pmc = 0
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
        n_pmc += 1
    log.info(f"PMC: {len(articles)} bajados, {n_pmc} con contenido útil")

    return docs


def main() -> None:
    docs = build_documents()
    if not docs:
        log.error("No se obtuvieron documentos. Revisa conectividad y credenciales NCBI.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    log.info(f"Split: {len(docs)} docs -> {len(chunks)} chunks")

    log.info(f"Cargando embeddings: {EMBEDDING_MODEL} (primera vez tarda más, descarga ~90 MB)")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    log.info(f"Indexando en {PERSIST_DIR}...")
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    log.info(f"✓ Índice listo en {PERSIST_DIR}")
    log.info("Siguiente paso: python -m rag.chatbot")


if __name__ == "__main__":
    main()
