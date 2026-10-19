
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel, Field

from rag import search


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="Cross-Lingual Hindi RAG API")

# Serve frontend CSS and JavaScript.
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "Hindi RAG",
    }


@app.post("/api/ask")
def ask_question(request: QuestionRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Please enter a question.",
        )

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing from the local .env file.",
        )

    started = time.perf_counter()

    try:
        # Retrieve relevant evidence using the existing RAG pipeline.
        hits = search(question, k=5)

        if not hits:
            return {
                "question": question,
                "answer": "No relevant evidence was found in the document.",
                "sources": [],
                "elapsed_seconds": round(
                    time.perf_counter() - started, 2
                ),
            }

        sources = [
            {
                "chunk_id": hit["chunk_id"],
                "page": hit["page"],
                "section": hit["section_title"],
                "score": round(float(hit["score"]), 4),
                "content": hit["content"],
            }
            for hit in hits
        ]

        evidence = "\n\n".join(
            (
                f"[Source {i}]\n"
                f"Page: {source['page']}\n"
                f"Section: {source['section']}\n"
                f"Chunk ID: {source['chunk_id']}\n"
                f"Content: {source['content']}"
            )
            for i, source in enumerate(sources, start=1)
        )

        prompt = f"""
You are a question-answering assistant for a Hindi document.

Instructions:
- Answer using only the evidence provided below.
- The source document is in Hindi, but the question may be in English.
- Respond in the same language as the question.
- Do not invent facts.
- If the evidence is insufficient, say so clearly.
- Keep the answer concise and useful.

Question:
{question}

Retrieved evidence:
{evidence}
"""

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        answer = (response.text or "").strip()

        if not answer:
            raise RuntimeError("Gemini returned an empty answer.")

        return {
            "question": question,
            "answer": answer,
            "sources": sources,
            "elapsed_seconds": round(
                time.perf_counter() - started, 2
            ),
        }

    except HTTPException:
        raise

    except Exception as exc:
        # Full details go to the server terminal, not the public response.
        print(
            f"RAG request failed: {type(exc).__name__}: {exc}",
            flush=True,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The question could not be processed. "
                "Check the backend terminal for the error."
            ),
        ) from exc
