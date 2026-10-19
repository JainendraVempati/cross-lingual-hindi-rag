"""
rag.py — semantic chunking, BGE-M3 embeddings, ChromaDB retrieval, and retrieval evaluation.

Colab usage (upload this file and final_document.json to /content):
    !pip -q install FlagEmbedding chromadb
    !python rag.py chunk
    !python rag.py index
    !python rag.py search "When did Kalam receive the Bharat Ratna?"
    !python rag.py demo
    !python rag.py eval

Safety:
- Reads final_document.json from /content or data/processed/.
- Writes semantic_chunks.json, NOT chunks.json, so an existing baseline is preserved.
- Does not edit or repair extracted source text.
- Skipping is based on record content/metadata, not assumed page numbers.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent
INPUT_CANDIDATES = [
    BASE / "final_document.json",
    BASE / "data" / "processed" / "final_document.json",
]

CHUNKS_FILE = BASE / "data" / "processed" / "semantic_chunks.json"
CHROMA_DIR = BASE / "data" / "processed" / "chroma_db_semantic"
COLLECTION = "kalam_hindi_semantic"
MODEL_NAME = "BAAI/bge-m3"

# Tune only after inspecting the printed chunk boundaries.
MIN_SECTION_CHARS = 120
LINE_UNIT_MAX = 450
MIN_CHARS = 250
HEADING_MIN_CHARS = 120
MAX_CHARS = 1100
SPLIT_PERCENTILE = 25
TOP_K = 5
EMBED_BATCH_SIZE = 8
EMBED_MAX_LENGTH = 1024

SENTENCE_END = ("।", "॥", "?", "!")
SPLIT_AFTER_END = re.compile(r'(?<=[।॥?!])\s+')

# These are retrieval checks, not a gold-standard evaluation set.
# Verify every query and expected answer against the assignment PDF/source document.
REQUIRED = [
    ("SLV-III ने किस उपग्रह को कक्षा में स्थापित किया और किस वर्ष?", [["रोहिणी"]]),
    ("कलाम को भारत रत्न किस वर्ष प्राप्त हुआ?", [["भारत रत्न", "1997"]]),
    ("पोखरण-II में कलाम की क्या भूमिका थी?", [["संगठनात्मक भूमिका"], ["केंद्रीय भूमिका"]]),
    ("Which institution did Kalam attend to study aeronautical engineering?", [["मद्रास इंस्टीट्यूट"]]),
    ("Who co-wrote the autobiography, and in what year was it published?", [["अरुण तिवारी"]]),
    ("How and where did Kalam die in 2015?", [["शिलांग"]]),
]

_model = None


def find_input() -> Path:
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path
    searched = "\n".join(f"  - {p}" for p in INPUT_CANDIDATES)
    raise FileNotFoundError(
        "Could not find final_document.json. Upload it beside rag.py or place it in "
        f"data/processed/.\nSearched:\n{searched}"
    )


def load_model():
    global _model
    if _model is None:
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as exc:
            raise RuntimeError(
                "FlagEmbedding is missing. In Colab run: !pip -q install FlagEmbedding"
            ) from exc
        print(f"Loading {MODEL_NAME}; first run downloads model weights.")
        _model = BGEM3FlagModel(MODEL_NAME, use_fp16=False)
    return _model


def embed(texts: list[str], batch_size: int = EMBED_BATCH_SIZE) -> np.ndarray:
    """Return normalized BGE-M3 dense vectors; normalization makes dot product cosine similarity."""
    if not texts:
        return np.empty((0, 1024), dtype=np.float32)
    model = load_model()
    output = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        encoded = model.encode(
            batch, batch_size=batch_size, max_length=EMBED_MAX_LENGTH
        )["dense_vecs"]
        output.append(np.asarray(encoded, dtype=np.float32))
    vectors = np.concatenate(output, axis=0)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value)).strip()


def get_record_text(record: dict) -> str:
    value = record.get("text", "")
    if isinstance(value, str):
        return value.strip()
    return ""


def is_question_or_contents_record(record: dict) -> bool:
    """Exclude clearly labelled contents and standalone question records."""
    text = get_record_text(record)
    normalized = re.sub(r"\\s+", " ", text).strip().lower()
    title = clean_text(record.get("section_title", "")).lower()

    contents_markers = ("विषय-सूची", "विषय सूची", "contents")
    question_markers = (
        "विचार एवं बोध-प्रश्न",
        "विचार एवं बोध प्रश्न",
        "बहुविकल्पीय प्रश्न",
    )

    # A contents record is excluded only when its beginning identifies it as contents.
    if any(marker in normalized[:120] for marker in contents_markers):
        return True

    # Exclude a standalone question section by its heading or section title.
    if any(marker in title or marker in normalized[:180] for marker in question_markers):
        return True

    return False


def skip_reason(record: dict) -> str | None:
    """Skip empty records, short footer-like records, and identified contents/questions."""
    text = get_record_text(record)

    if not text:
        return "empty prose text"

    if is_question_or_contents_record(record):
        return "clearly labelled contents/question material"

    # Skip only short records that look like publication/footer metadata.
    normalized = re.sub(r"\\s+", " ", text).strip()
    footer_markers = (
        "मौलिक अध्ययन सहायिका",
        "पुस्तक का पुनरुत्पादन नहीं",
        "नमूना हिंदी RAG दस्तावेज़",
    )
    if len(normalized) < 200 and any(marker in normalized for marker in footer_markers):
        return "short publication/footer text"

    if len(text) < MIN_SECTION_CHARS:
        return f"short record ({len(text)} chars; possible footer)"

    return None

def ends_sentence(line: str) -> bool:
    return line.rstrip('"”’) ').endswith(SENTENCE_END)


def make_units(text: str) -> list[str]:
    """Split prose conservatively into line/sentence units; never use a dictionary to alter text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    units: list[str] = []
    pending_heading = ""
    for index, line in enumerate(lines):
        # Treat a short non-sentence-ending line as a possible heading, but retain it with following text.
        if not ends_sentence(line) and len(line) <= 80 and index < len(lines) - 1:
            pending_heading = f"{pending_heading} {line}".strip()
            continue

        if len(line) <= LINE_UNIT_MAX:
            pieces = [line]
        else:
            pieces = [part.strip() for part in SPLIT_AFTER_END.split(line) if part.strip()]

        if pending_heading and pieces:
            pieces[0] = pending_heading + "\n" + pieces[0]
            pending_heading = ""
        units.extend(pieces)

    if pending_heading:
        if units:
            units[-1] = units[-1] + "\n" + pending_heading
        else:
            units.append(pending_heading)
    return units


def split_section(units: list[str], similarities: np.ndarray, threshold: float) -> list[list[str]]:
    if not units:
        return []
    groups: list[list[str]] = []
    current: list[str] = []

    for i, unit in enumerate(units):
        current_size = len(" ".join(current))
        too_long = bool(current) and current_size + 1 + len(unit) > MAX_CHARS
        heading_start = bool(current) and "\n" in unit and current_size >= HEADING_MIN_CHARS
        topic_change = (
            bool(current)
            and i > 0
            and i - 1 < len(similarities)
            and similarities[i - 1] < threshold
            and current_size >= MIN_CHARS
        )
        if too_long or heading_start or topic_change:
            groups.append(current)
            current = []
        current.append(unit)

    if current:
        groups.append(current)

    # Merge a small final chunk only when the combined size stays within MAX_CHARS.
    if len(groups) > 1 and len(" ".join(groups[-1])) < MIN_CHARS and "\n" not in groups[-1][0]:
        combined = " ".join(groups[-2] + groups[-1])
        if len(combined) <= MAX_CHARS:
            groups[-2].extend(groups.pop())

    # Final safety check: split any oversized group at whitespace boundaries.
    safe_groups = []
    for group in groups:
        text = " ".join(group).strip()
        while len(text) > MAX_CHARS:
            cut = text.rfind(" ", 0, MAX_CHARS + 1)
            if cut <= 0:
                cut = MAX_CHARS
            safe_groups.append([text[:cut].strip()])
            text = text[cut:].strip()
        if text:
            safe_groups.append([text])
    return safe_groups


def table_row_chunks(table: dict) -> list[dict]:
    cells = table.get("cells") or []
    if len(cells) < 2:
        return []
    header = [clean_text(x) for x in cells[0]]
    page = int(table.get("page", 0) or 0)
    table_index = int(table.get("table_index", 0) or 0)
    title = clean_text(table.get("section_title")) or "तालिका"
    chunks = []

    for row_index, row in enumerate(cells[1:], start=1):
        parts = []
        for col_index, value in enumerate(row):
            value = clean_text(value)
            label = header[col_index] if col_index < len(header) and header[col_index] else f"Column {col_index + 1}"
            if value and value not in ("—", "-"):
                parts.append(f"{label}: {value}")
        if not parts:
            continue
        content = " | ".join([title] + parts)
        chunks.append({
            "chunk_id": f"table_p{page}_t{table_index}_r{row_index}",
            "chunk_type": "table_row",
            "page": page,
            "section_no": table.get("section_no"),
            "section_title": title,
            "content": content,
            "embed_text": content,
            "table_index": table_index,
            "row_index": row_index,
        })
    return chunks


def build_chunks() -> list[dict]:
    source_path = find_input()
    with source_path.open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError("Expected final_document.json to contain a JSON list of records.")

    prose_records, tables, skipped = [], [], []
    for record in records:
        if not isinstance(record, dict):
            skipped.append(("unknown", "record is not an object"))
            continue
        if record.get("type") == "table":
            tables.append(record)
            continue
        reason = skip_reason(record)
        if reason:
            skipped.append((record.get("page", "unknown"), reason))
        else:
            prose_records.append(record)

    units_by_record = [make_units(get_record_text(r)) for r in prose_records]
    # Embed each record's units separately. This limits peak memory and avoids cross-record comparisons.
    chunks: list[dict] = []
    per_page_counter: dict[int, int] = {}
    total_units = sum(len(units) for units in units_by_record)
    print(f"Input: {source_path}")
    print(f"Records: {len(records)} | prose records retained: {len(prose_records)} | tables: {len(tables)}")
    print(f"Embedding {total_units} prose units in small batches for semantic boundary detection ...")

    for record, units in zip(prose_records, units_by_record):
        if not units:
            skipped.append((record.get("page", "unknown"), "no usable text units"))
            continue
        vectors = embed(units)
        similarities = (
            (vectors[:-1] * vectors[1:]).sum(axis=1)
            if len(vectors) > 1 else np.empty((0,), dtype=np.float32)
        )
        threshold = float(np.percentile(similarities, SPLIT_PERCENTILE)) if similarities.size else -1.0
        for group in split_section(units, similarities, threshold):
            content = " ".join(group).strip()
            if not content:
                continue
            page = int(record.get("page", 0) or 0)
            per_page_counter[page] = per_page_counter.get(page, 0) + 1
            section_no = record.get("section_no")
            section_title = clean_text(record.get("section_title")) or "अज्ञात अनुभाग"
            chunks.append({
                "chunk_id": f"prose_p{page}_c{per_page_counter[page]}",
                "chunk_type": "prose",
                "page": page,
                "section_no": section_no,
                "section_title": section_title,
                "content": content,
                "embed_text": f"{section_title}\n{content}",
            })

    for table in tables:
        chunks.extend(table_row_chunks(table))

    chunks.sort(key=lambda c: (c["page"], c["chunk_type"] == "table_row", c["chunk_id"]))
    if not chunks:
        raise ValueError("No chunks were created. Check the input file and skip rules.")

    # Deliberately use a different filename from the existing baseline chunks.json.
    CHUNKS_FILE.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nSaved {len(chunks)} semantic chunks to {CHUNKS_FILE}")
    print(f"  prose chunks: {sum(c['chunk_type'] == 'prose' for c in chunks)}")
    print(f"  table-row chunks: {sum(c['chunk_type'] == 'table_row' for c in chunks)}")
    print(f"  empty chunks: {sum(not c['content'].strip() for c in chunks)}")
    print(f"  duplicate IDs: {len(chunks) - len({c['chunk_id'] for c in chunks})}")
    print("\nSkipped records (review this list; pages are not hardcoded):")
    if skipped:
        for page, reason in skipped:
            print(f"  page {page}: {reason}")
    else:
        print("  none")

    print("\nProse chunk previews (inspect where the cuts occur):")
    for chunk in chunks:
        if chunk["chunk_type"] == "prose":
            section = chunk["section_no"] if chunk["section_no"] is not None else "-"
            print(
                f"  {chunk['chunk_id']:<18} section {section!s:>3} | "
                f"{len(chunk['content']):>4} chars | {chunk['content'][:90]!r}"
            )
    return chunks


def get_collection(reset: bool = False):
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as exc:
        raise RuntimeError("ChromaDB is missing. In Colab run: !pip -q install chromadb") from exc

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
        return client.create_collection(
            COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    try:
        return client.get_collection(COLLECTION)
    except Exception as exc:
        raise RuntimeError("Semantic index not found. Run `python rag.py index` first.") from exc


def chroma_metadata(chunk: dict) -> dict:
    """Chroma metadata cannot contain None; omit unavailable values."""
    meta = {
        "page": int(chunk.get("page", 0) or 0),
        "chunk_type": str(chunk.get("chunk_type", "prose")),
    }
    if chunk.get("section_no") is not None:
        try:
            meta["section_no"] = int(chunk["section_no"])
        except (TypeError, ValueError):
            meta["section_no"] = str(chunk["section_no"])
    if chunk.get("section_title"):
        meta["section_title"] = str(chunk["section_title"])
    if chunk.get("table_index") is not None:
        meta["table_index"] = int(chunk["table_index"])
    if chunk.get("row_index") is not None:
        meta["row_index"] = int(chunk["row_index"])
    return meta


def index_chunks() -> None:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError("semantic_chunks.json not found. Run `python rag.py chunk` first.")
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    if not chunks:
        raise ValueError("semantic_chunks.json is empty.")
    collection = get_collection(reset=True)
    print(f"Embedding and indexing {len(chunks)} chunks ...")
    # Batch embeddings and Chroma writes to limit memory usage.
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start:start + EMBED_BATCH_SIZE]
        vectors = embed([item["embed_text"] for item in batch])
        collection.add(
            ids=[item["chunk_id"] for item in batch],
            embeddings=vectors.tolist(),
            documents=[item["content"] for item in batch],
            metadatas=[chroma_metadata(item) for item in batch],
        )
        print(f"  indexed {min(start + len(batch), len(chunks))}/{len(chunks)}")
    print(f"Stored {collection.count()} chunks in {CHROMA_DIR} (collection: {COLLECTION})")


def search(query: str, k: int = TOP_K) -> list[dict]:
    if k < 1:
        raise ValueError("k must be at least 1.")
    query = unicodedata.normalize("NFC", " ".join(query.split()))
    collection = get_collection()
    query_vector = embed([query])[0].tolist()
    result = collection.query(
        query_embeddings=[query_vector],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for i, chunk_id in enumerate(result["ids"][0]):
        metadata = result["metadatas"][0][i] or {}
        distance = float(result["distances"][0][i])
        hits.append({
            "chunk_id": chunk_id,
            "score": 1.0 - distance,
            "page": metadata.get("page", "?"),
            "section_no": metadata.get("section_no", "-"),
            "section_title": metadata.get("section_title", "अज्ञात अनुभाग"),
            "chunk_type": metadata.get("chunk_type", "prose"),
            "content": result["documents"][0][i] or "",
        })
    return hits


def show(query: str, hits: list[dict], preview: int = 260) -> None:
    print(f"\nQuery: {query}")
    if not hits:
        print("  No results.")
        return
    for rank, hit in enumerate(hits, start=1):
        print(
            f"  {rank}. cosine similarity {hit['score']:.3f} | page {hit['page']} | "
            f"section {hit['section_no']}: {hit['section_title']} | "
            f"{hit['chunk_type']} | chunk_id {hit['chunk_id']}"
        )
        print(f"     {hit['content'][:preview]!r}")






def generate_answer(query: str, k: int = TOP_K) -> dict:
    """Generate an evidence-grounded answer using Gemini and attach source metadata."""
    import os
    import time
    from dotenv import load_dotenv
    from google import genai

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to your .env file."
        )

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    hits = search(query, k=k)

    if not hits:
        return {
            "query": query,
            "answer": "No relevant evidence was retrieved.",
            "sources": [],
            "elapsed_seconds": 0.0,
        }

    context_parts = []
    for hit in hits:
        context_parts.append(
            f"[Chunk ID: {hit['chunk_id']} | "
            f"Page: {hit['page']} | "
            f"Section: {hit['section_title']} | "
            f"Similarity: {hit['score']:.3f}]\n"
            f"{hit['content']}"
        )

    context = "\n\n".join(context_parts)

    prompt = f"""
You answer questions using only evidence from a Hindi document.

Rules:
1. Use only the supplied evidence. Do not use outside knowledge.
2. Read all supplied chunks before answering.
3. Prefer direct statements in the evidence over assumptions.
4. Do not guess names, institutions, dates, places, or numbers.
5. Answer in the same language as the question.
6. Include every detail requested by the question when the evidence supports it.
7. If the evidence is incomplete or contradictory, clearly say so.
8. Similarity scores indicate retrieval relevance, not factual certainty.
9. Do not invent chunk IDs or citations.
10. The application will append source citations from retrieved metadata.

RETRIEVED EVIDENCE:
{context}

QUESTION:
{query}

Answer concisely, using only the retrieved evidence.
"""

    start = time.perf_counter()

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "temperature": 0,
        },
    )

    answer = (response.text or "").strip()
    if not answer:
        answer = "The model returned no answer; the evidence may be insufficient."

    elapsed = time.perf_counter() - start

    sources = [
        {
            "chunk_id": hit["chunk_id"],
            "page": hit["page"],
            "section_title": hit["section_title"],
            "score": round(hit["score"], 3),
        }
        for hit in hits
    ]

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "elapsed_seconds": round(elapsed, 3),
    }





def format_answer(result: dict) -> str:
    """Format a generated answer with citations from retrieval metadata."""
    lines = [
        f"## {result['query']}",
        "",
        result["answer"],
        "",
        "**Retrieved sources:**",
    ]

    for source in result["sources"]:
        lines.append(
            f"- Page {source['page']} — "
            f"{source['section_title']} — "
            f"Chunk ID: `{source['chunk_id']}` "
            f"(similarity: {source['score']:.3f})"
        )

    lines.extend([
        "",
        f"*Generation time: {result['elapsed_seconds']:.3f} seconds*",
        "",
        "---",
        "",
    ])

    return "\n".join(lines)




def squash(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))


def is_hit(content: str, alternatives: list[list[str]]) -> bool:
    compact_content = squash(content)
    return any(all(squash(term) in compact_content for term in group) for group in alternatives)


def demo() -> None:
    for query, _ in REQUIRED:
        show(query, search(query, k=3))


def evaluate() -> None:
    ranks = []
    for query, alternatives in REQUIRED:
        hits = search(query, k=5)
        rank = next(
            (i for i, hit in enumerate(hits, start=1) if is_hit(hit["content"], alternatives)),
            None,
        )
        ranks.append(rank)
        print(f"{'hit at rank ' + str(rank) if rank else 'MISS (not in top 5)':<22} {query}")

    total = len(ranks)
    for k in (1, 3, 5):
        count = sum(1 for rank in ranks if rank is not None and rank <= k)
        print(f"Hit@{k}: {count}/{total} ({count / total:.1%})")
    reciprocal_ranks = [1.0 / rank for rank in ranks if rank is not None]
    print(f"MRR: {sum(reciprocal_ranks) / total:.3f}")
    print("Note: these metrics are only as reliable as the manually supplied queries and expected answer strings.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hindi RAG: semantic chunking, embedding, retrieval, evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("chunk", help="create semantic_chunks.json without overwriting chunks.json")
    commands.add_parser("index", help="embed semantic chunks and store them in ChromaDB")
    commands.add_parser("demo", help="run the six example queries")
    commands.add_parser("eval", help="evaluate retrieval on the six example queries")
    search_parser = commands.add_parser("search", help="retrieve the most relevant chunks")
    answer_parser = commands.add_parser(
        "answer",
        help="answer one question using Ollama and show citations",
    )
    answer_parser.add_argument("query")
    answer_parser.add_argument("-k", type=int, default=TOP_K)

    commands.add_parser(
        "answers",
        help="answer all six assignment questions and save answers.md",
    )
    search_parser.add_argument("query")
    search_parser.add_argument("-k", type=int, default=TOP_K)
    args = parser.parse_args()

    try:
        if args.command == "chunk":
            build_chunks()
        elif args.command == "index":
            index_chunks()
        elif args.command == "answer":
            result = generate_answer(args.query, k=args.k)
            print(format_answer(result))

        elif args.command == "answers":
            questions = [
                "SLV-III ने किस उपग्रह को कक्षा में स्थापित किया और किस वर्ष?",
                "कलाम को भारत रत्न किस वर्ष प्राप्त हुआ?",
                "पोखरण-II में कलाम की क्या भूमिका थी?",
                "Which institution did Kalam attend to study aeronautical engineering?",
                "Who co-wrote the autobiography, and in what year was it published?",
                "How and where did Kalam die in 2015?",
            ]

            output = []
            for i, question in enumerate(questions, start=1):
                print(f"\nProcessing question {i}/{len(questions)}: {question}")
                result = generate_answer(question)
                output.append(format_answer(result))

            output_path = BASE / "answers.md"
            output_path.write_text(
                "\n".join(output),
                encoding="utf-8",
            )
            print(f"\nSaved answers and citations to: {output_path}")
        elif args.command == "search":
            show(args.query, search(args.query, k=args.k))
        elif args.command == "demo":
            demo()
        elif args.command == "eval":
            evaluate()
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
