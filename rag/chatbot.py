"""
CLI interactiva del chatbot RAG. Streamea la respuesta token por token.

Uso:
    python -m rag.chatbot
"""
import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama

from config import (
    PERSIST_DIR, EMBEDDING_MODEL,
    RETRIEVER_K, RETRIEVER_FETCH_K, RETRIEVER_LAMBDA,
    OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL,
)

logging.basicConfig(level=logging.WARNING)

SYSTEM = """Eres un asistente clínico-científico especializado en anemia falciforme (sickle cell anemia).

Reglas estrictas:
- Responde EXCLUSIVAMENTE con base en el CONTEXTO proporcionado.
- Si la información no está en el CONTEXTO, di: "No tengo información sobre esto en mis fuentes."
- Sé técnico, conciso y usa terminología clínica/bioquímica correcta (HbS, vaso-oclusión, hidroxiurea, etc.).
- Al final SIEMPRE cita las fuentes con [PMCxxxx] o la URL, según corresponda.
- Si la pregunta es ambigua, pídelo aclaración antes de responder.

CONTEXTO:
{context}
"""


def format_docs(docs) -> str:
    """Formatea los chunks recuperados con su ID/URL para que el LLM pueda citarlos."""
    return "\n\n---\n\n".join(
        f"[{d.metadata.get('id') or d.metadata.get('source')}]\n{d.page_content}"
        for d in docs
    )


def build_chain():
    """Construye el chain LCEL: retriever + prompt + LLM + parser."""
    if not PERSIST_DIR.exists():
        raise FileNotFoundError(
            f"No existe el índice en {PERSIST_DIR}.\n"
            "Corre primero:  python -m rag.build_index"
        )
    if not OLLAMA_API_KEY:
        raise RuntimeError(
            "Falta OLLAMA_API_KEY.\n"
            "1. Copia .env.example a .env\n"
            "2. Obtén tu key en https://ollama.com/settings/keys\n"
            "3. Pégala en .env"
        )

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = Chroma(
        persist_directory=str(PERSIST_DIR),
        embedding_function=embeddings,
    )
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": RETRIEVER_K,
            "fetch_k": RETRIEVER_FETCH_K,
            "lambda_mult": RETRIEVER_LAMBDA,
        },
    )

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_HOST,
        client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_API_KEY}"}},
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM),
        ("human", "{question}"),
    ])

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


def main() -> None:
    print(f"\n{'=' * 60}")
    print(f"  Sickle Cell RAG  |  modelo: {OLLAMA_MODEL}")
    print(f"  fuentes: PMC (2016-2026) + NHLBI")
    print(f"  comandos: 'salir' para terminar")
    print(f"{'=' * 60}\n")

    try:
        chain = build_chain()
    except (FileNotFoundError, RuntimeError) as e:
        print(f"ERROR: {e}")
        return

    while True:
        try:
            q = input("Tú> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in {"salir", "exit", "quit", "q"}:
            break

        try:
            print("\nAsistente> ", end="", flush=True)
            for chunk in chain.stream(q):
                print(chunk, end="", flush=True)
            print("\n")
        except Exception as e:
            print(f"\n[ERROR durante la respuesta] {e}\n")


if __name__ == "__main__":
    main()
