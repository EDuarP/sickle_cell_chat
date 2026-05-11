# 🩸 Sickle Cell Chat (RAG Medical Bot)

Chatbot inteligente especializado en el diagnóstico y tratamiento de la anemia falciforme, diseñado para proporcionar respuestas basadas en evidencia médica real mediante la técnica de **RAG (Retrieval-Augmented Generation)**.

## 🚀 Características principales

- **RAG Pipeline:** El sistema no depende solo del conocimiento interno del LLM; busca información relevante en una base de datos de documentos médicos antes de generar la respuesta, reduciendo drásticamente las alucinaciones.
- **Sourcing Automatizado:** Incluye un scraper personalizado para **PubMed Central (PMC)** que extrae la literatura científica más reciente sobre anemia falciforme.
- **Indexación Eficiente:** Implementa un proceso de construcción de índices (Vector DB) para permitir búsquedas semánticas rápidas y precisas.
- **Arquitectura Desacoplada:**
    - **Backend:** FastAPI para una API rápida y escalable.
    - **Frontend:** Interfaz web minimalista y responsiva para una interacción fluida.
    - **RAG Engine:** Módulo dedicado al procesamiento de documentos y recuperación de contexto.

## 🛠️ Stack Tecnológico

- **Backend:** FastAPI, Python.
- **RAG:** LangChain / Vector Store (para la recuperación de fragmentos de texto).
- **Data Sourcing:** Custom scrapers para PubMed Central (PMC).
- **Frontend:** HTML, CSS y JavaScript vanilla para máxima ligereza.

## 📦 Instalación y Ejecución

1. Clona el repositorio.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Construye el índice de documentos:
   ```bash
   python rag/build_index.py
   ```
4. Ejecuta la aplicación:
   ```bash
   bash run.sh
   ```

## 🩺 Propósito
Este proyecto busca democratizar el acceso a información médica validada sobre la anemia falciforme, permitiendo que pacientes y profesionales consulten literatura científica de manera conversacional y eficiente.
