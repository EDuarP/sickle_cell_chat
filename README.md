# Sickle Cell Chat — RAG biomédico

Chatbot RAG sobre anemia falciforme. Fuente:

- **PMC (PubMed Central)** vía NCBI E-utilities — artículos 2016-2026 ordenados por relevancia, **API oficial** (no HTML scraping).

Stack:

- **LangChain** (LCEL) — orquestación
- **Chroma** — vector store local persistente
- **HuggingFace `all-MiniLM-L6-v2`** — embeddings
- **Ollama Cloud** (`gpt-oss:120b` por defecto) — LLM

---

## Setup

```bash
cd ~/Documents/Personal/sickle_cell_chat

# 1. Virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 2. Dependencias (la primera vez tarda ~2-3 min)
pip install --upgrade pip
pip install -r requirements.txt

# 3. Credenciales
cp .env.example .env
```

Edita `.env` y configura:

| Variable | Cómo obtener |
|---|---|
| `NCBI_EMAIL` | Tu email personal. NCBI lo exige pero no lo verifica. |
| `OLLAMA_API_KEY` | https://ollama.com/settings/keys (necesitas cuenta en ollama.com) |
| `NCBI_API_KEY` *(opcional)* | https://www.ncbi.nlm.nih.gov/account/settings/ → "API Key Management". Sube el rate limit de 3 a 10 req/s. |

---

## Uso

### Paso 1 — Construir el índice (una sola vez)

```bash
python -m rag.build_index
```

Pasa por:
1. `esearch` en PMC → trae ~30 PMCIDs sobre `sickle cell anemia` (2016-2026).
2. `efetch` cada uno → parsea JATS XML (título + abstract + body).
3. Splitter recursivo → chunks de 1000 chars con overlap 150.
4. Embeddings con MiniLM (descarga el modelo la primera vez, ~90 MB).
5. Persiste Chroma en `./chroma_sickle_cell/`.

Tarda ~2-3 min según red.

### Paso 2 — Chat

```bash
python -m rag.chatbot
```

```
============================================================
  Sickle Cell RAG  |  modelo: gpt-oss:120b
  fuente: PMC (2016-2026)
  comandos: 'salir' para terminar
============================================================

Tú> ¿Cuál es el mecanismo de la vaso-oclusión en HbSS?

Asistente> ...streaming token a token...
```

---

## Smoke tests (probar cada módulo aislado)

```bash
# Solo el scraper PMC (trae 3 artículos y los imprime)
python -m scrapers.pmc_scraper
```

---

## Estructura

```
sickle_cell_chat/
├── .env                    # secretos (no commitear)
├── .env.example
├── .gitignore
├── config.py               # settings centralizados
├── requirements.txt
├── README.md
├── scrapers/
│   ├── __init__.py
│   └── pmc_scraper.py      # NCBI E-utilities (BioPython)
├── rag/
│   ├── __init__.py
│   ├── build_index.py      # pipeline de indexación
│   └── chatbot.py          # CLI interactiva con streaming
└── chroma_sickle_cell/     # (generado por build_index)
```

---

## Ajustes comunes

Todo está en `config.py`:

- **Cambiar modelo LLM** → `OLLAMA_MODEL` en `.env`. Opciones: `gpt-oss:120b`, `gpt-oss:20b`, `deepseek-v3.1:671`, `qwen3-coder:480b`.
- **Más artículos de PMC** → sube `PMC_RETMAX` en `config.py`.
- **Embeddings biomédicos** (mejor recall) → cambia `EMBEDDING_MODEL` a `"pritamdeka/S-PubMedBert-MS-MARCO"`. Tienes que **reconstruir el índice**.
- **Chunks más grandes** → ajusta `CHUNK_SIZE` y reconstruye índice.
- **Más contexto al LLM** → sube `RETRIEVER_K` (cuidado con la ventana del modelo).

---

## Reindexar con datos frescos

```bash
rm -rf chroma_sickle_cell/
python -m rag.build_index
```

---

## Troubleshooting

**`NCBI_EMAIL no configurado`** → falta editar `.env`.

**`Falta OLLAMA_API_KEY`** → genera la key en https://ollama.com/settings/keys y pégala en `.env`.

**`HTTP 429` en PMC** → te pasaste del rate limit. Agrega `NCBI_API_KEY` en `.env`.

**`No se obtuvieron documentos`** → revisa conectividad y que el `NCBI_EMAIL` sea válido. NCBI bloquea agentes sin email.

**Respuestas pobres / "no tengo información"** → el retrieval no encuentra. Sube `RETRIEVER_K` a 8-10, o cambia el modelo de embeddings al biomédico.

**El LLM responde en inglés** → es normal con `gpt-oss` para textos en inglés (las fuentes lo están). Agrega al `SYSTEM` en `chatbot.py`: "Responde siempre en español aunque el contexto esté en inglés."

---

## Siguiente paso

Cuando el backend funcione, agregamos un frontend (Gradio o Streamlit) y opcionalmente lo deployamos a HF Spaces.
