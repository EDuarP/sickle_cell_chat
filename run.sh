#!/usr/bin/env bash
# Sickle Cell RAG — arranque local
#
#   ./run.sh              -> levanta el server (frontend + API) en :8000
#   PORT=9000 ./run.sh    -> cambia puerto
#   SKIP_INSTALL=1 ./run.sh -> salta pip install
#
# La indexación de PMC + descarga del modelo de embeddings se dispara
# desde el botón "Inicializar" del frontend (no se hace aquí).

set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

# ---------- venv ----------
if [ ! -d ".venv" ]; then
  echo "[run] creando virtualenv en .venv/"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# ---------- .env ----------
if [ ! -f ".env" ]; then
  cat <<EOF
[run] ERROR: no existe .env

Crea uno con al menos:
  NCBI_EMAIL=tu_email@dominio.com
  OLLAMA_API_KEY=tu_key_de_ollama_cloud
  NCBI_API_KEY=opcional_pero_recomendado
EOF
  exit 1
fi

# ---------- deps ----------
if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  echo "[run] instalando dependencias…"
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
fi

# ---------- chequeo de credenciales ----------
python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env")
missing = [k for k in ("NCBI_EMAIL", "OLLAMA_API_KEY") if not os.environ.get(k, "").strip()]
if missing:
    print(f"[run] ERROR: faltan variables en .env: {', '.join(missing)}")
    raise SystemExit(1)
PY

# ---------- arranque ----------
echo ""
echo "[run] abriendo http://${HOST}:${PORT}"
echo "[run] la primera vez pulsa 'Inicializar' en la web para descargar"
echo "      artículos de PMC + el modelo de embeddings (~90 MB)."
echo ""

exec uvicorn api.server:app --host "$HOST" --port "$PORT"
