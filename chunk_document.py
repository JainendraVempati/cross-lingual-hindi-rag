
import json
import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "data" / "processed" / "final_document.json"
OUTPUT_FILE = ROOT / "data" / "processed" / "chunks.json"

TARGET_CHARS = 1400
MAX_CHARS = 2000
OVERLAP_CHARS = 200
TABLE_ROWS_PER_CHUNK = 5


def load_document():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError("Expected final_document.json to contain a list.")

    return records


def normalize_whitespace(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()





def split_prose(text):
    text = normalize_whitespace(text)

    if not text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    pieces = []

    for paragraph in paragraphs:
        sentences = re.split(r"(?<=[।!?])\s+", paragraph)
        current = ""

        for sentence in sentences:
            if len(sentence) > MAX_CHARS:
                if current:
                    pieces.append(current)
                    current = ""

                remaining = sentence

                while len(remaining) > MAX_CHARS:
                    split_at = remaining.rfind(" ", 0, MAX_CHARS + 1)

                    if split_at <= 0:
                        split_at = MAX_CHARS

                    pieces.append(remaining[:split_at].strip())
                    remaining = remaining[split_at:].strip()

                if remaining:
                    current = remaining

                continue

            candidate = f"{current} {sentence}".strip()

            if current and len(candidate) > TARGET_CHARS:
                pieces.append(current)
                current = sentence
            else:
                current = candidate

        if current:
            pieces.append(current)

    chunks = []
    current = ""

    for piece in pieces:
        candidate = f"{current}\n\n{piece}".strip()

        if current and len(candidate) > TARGET_CHARS:
            chunks.append(current)
            current = piece
        else:
            current = candidate

    if current:
        chunks.append(current)

    if OVERLAP_CHARS <= 0 or len(chunks) < 2:
        return chunks

    overlapped_chunks = [chunks[0]]

    for chunk in chunks[1:]:
        previous = overlapped_chunks[-1]
        overlap_start = max(0, len(previous) - OVERLAP_CHARS)
        overlap_text = previous[overlap_start:].strip()

        if " " in overlap_text:
            overlap_text = overlap_text[overlap_text.find(" ") + 1:]

        overlapped_chunks.append(
            f"{overlap_text} {chunk}".strip() if overlap_text else chunk
        )

    return overlapped_chunks




def stable_chunk_id(record, index, content):
    key = (
        f"{record.get('page')}|{record.get('type')}|"
        f"{record.get('table_index', '')}|{index}|{content}"
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"chunk_{digest}"


def build_prose_chunks(record):
    text = record.get("text", "")
    chunks = split_prose(text)
    results = []

    for index, content in enumerate(chunks, start=1):
        item = {
            "chunk_id": stable_chunk_id(record, index, content),
            "content": content,
            "source_page": record["page"],
            "content_type": "prose",
            "chunk_index": index,
        }

        for field in ("section_no", "section_title"):
            if field in record:
                item[field] = record[field]

        results.append(item)

    return results


def build_table_chunks(record):
    cells = record.get("cells", [])

    if not cells:
        raise ValueError(
            f"Table on page {record.get('page')} has no cells."
        )

    headers = cells[0]
    data_rows = cells[1:]
    results = []

    for start in range(0, len(data_rows), TABLE_ROWS_PER_CHUNK):
        row_group = data_rows[start:start + TABLE_ROWS_PER_CHUNK]

        lines = [
            f"Table: {record.get('section_title', 'Untitled table')}",
            "Columns: " + " | ".join(str(cell) for cell in headers),
        ]

        for row in row_group:
            lines.append(" | ".join(str(cell).strip() for cell in row))

        content = "\n".join(lines)
        index = len(results) + 1

        item = {
            "chunk_id": stable_chunk_id(record, index, content),
            "content": content,
            "source_page": record["page"],
            "content_type": "table",
            "chunk_index": index,
            "table_index": record.get("table_index"),
            "section_title": record.get("section_title"),
            "section_no": record.get("section_no"),
            "row_start": start + 1,
            "row_end": start + len(row_group),
            "headers": headers,
        }

        results.append(item)

    return results


def main():
    records = load_document()
    all_chunks = []

    for record in records:
        record_type = record.get("type")

        if record_type == "prose":
            all_chunks.extend(build_prose_chunks(record))
        elif record_type == "table":
            all_chunks.extend(build_table_chunks(record))
        else:
            raise ValueError(
                f"Unknown record type: {record_type!r}"
            )

    ids = [chunk["chunk_id"] for chunk in all_chunks]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected.")

    if any(not chunk["content"].strip() for chunk in all_chunks):
        raise ValueError("Empty chunk detected.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(all_chunks, file, ensure_ascii=False, indent=2)

    print(f"Source records: {len(records)}")
    print(f"Chunks created: {len(all_chunks)}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Prose chunks: {sum(c['content_type'] == 'prose' for c in all_chunks)}")
    print(f"Table chunks: {sum(c['content_type'] == 'table' for c in all_chunks)}")
    print("Validation: passed")


if __name__ == "__main__":
    main()
