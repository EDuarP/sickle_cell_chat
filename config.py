"""Configuración centralizada. Lee de .env y expone constantes."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).parent.resolve()
PERSIST_DIR = BASE_DIR / "chroma_sickle_cell"

# --- NCBI ---
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "").strip()
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "").strip() or None

# --- Ollama Cloud ---
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "").strip()
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "https://ollama.com").strip()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:120b").strip()

# --- RAG / indexación ---
# Dos búsquedas: una general sobre la enfermedad, otra enfocada en tratamientos.
# Los PMCIDs se unen (deduplicados) antes de descargar.
QUERIES = [
    "sickle cell anemia",
    'sickle cell anemia AND (treatment OR therapy OR management OR hydroxyurea OR '
    'transfusion OR "gene therapy" OR voxelotor OR crizanlizumab OR '
    '"bone marrow transplant" OR "stem cell transplant")',
]
PMC_RETMAX = 30           # cuántos artículos por query
PMC_MINDATE = "2016"
PMC_MAXDATE = "2026"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# all-MiniLM-L6-v2 es rápido y general. Para mejor recall biomédico,
# considera "pritamdeka/S-PubMedBert-MS-MARCO" (más pesado, ~440MB).
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# --- Retrieval ---
RETRIEVER_K = 5           # chunks finales que ve el LLM
RETRIEVER_FETCH_K = 20    # candidatos antes del MMR
RETRIEVER_LAMBDA = 0.5    # 0 = max diversidad, 1 = max relevancia
