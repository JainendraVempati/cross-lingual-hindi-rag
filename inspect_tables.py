"""
extract_tables.py
Generic PyMuPDF table extraction, conservative cleaning, auditing, and row-record creation.

Run:
    $env:PYTHONUTF8 = "1"
    python extract_tables.py

No page numbers or Hindi word corrections are hardcoded.
Raw outputs are created only if they do not already exist.
Ambiguous OCR defects are not guessed or dictionary-corrected.
"""
import csv
import json
import re
import unicodedata
from pathlib import Path

import pymupdf

BASE = Path(__file__).resolve().parent
PDF_PATH = BASE / "data" / "Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf"
RAW_TABLES = BASE / "verification" / "raw_tables" / "tables_raw_clip.json"
RAW_PROSE = BASE / "verification" / "raw_pages" / "pymupdf_raw_tablepages.json"
CLEAN_TABLES = BASE / "data" / "processed" / "tables_clean.json"
AUDIT_FILE = BASE / "data" / "processed" / "tables_clean_audit.csv"
BREAKS_REVIEW_FILE = BASE / "data" / "processed" / "table_cell_breaks_review.csv"
ROWS_FILE = BASE / "data" / "processed" / "table_rows.json"
DISPLAY_FILE = BASE / "data" / "processed" / "tables_display.json"

CELL_INSET_POINTS = 1.0
# Unicode dependent vowel signs (matras); U+094D (virama) is excluded.
VOWEL_SIGNS = set(range(0x093E, 0x094D)) | {0x0962, 0x0963}
PUNCTUATION_ONLY = set(" \t.,;:!?()[]{}\"'“”‘’–—-।॥")


def write_json(path: Path, value) -> None:
    """Write readable UTF-8 JSON, creating parent folders as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path):
    """Read UTF-8 JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def rule_a(text: str) -> str:
    """Apply NFC and remove immediately repeated identical dependent vowel signs."""
    text = unicodedata.normalize("NFC", text)
    output = []
    for char in text:
        if output and ord(char) in VOWEL_SIGNS and char == output[-1]:
            continue
        output.append(char)
    return "".join(output)


def extract_cell_text(page, cell):
    """Extract text inside a cell rectangle; merged cells return an empty string."""
    if cell is None:
        return ""
    rect = pymupdf.Rect(cell)
    inset = min(CELL_INSET_POINTS, rect.width / 4, rect.height / 4)
    rect = rect + (inset, inset, -inset, -inset)
    if rect.is_empty or rect.is_infinite:
        return ""
    return page.get_text("text", clip=rect)


def find_tables(page):
    """Detect ruled tables; ignore detections smaller than 2 rows by 2 columns."""
    return [
        table for table in page.find_tables(strategy="lines").tables
        if table.row_count >= 2 and table.col_count >= 2
    ]





def page_heading(page, table_bbox):
    """Extract the section heading immediately above the body text."""
    blocks = [
        block for block in page.get_text("blocks")
        if block[6] == 0
        and block[3] <= table_bbox[1]
        and block[4].strip()
    ]

    if not blocks:
        return ""

    blocks.sort(key=lambda block: (block[1], block[0]))

    # The section heading is visually separated from the body text.
    first_block = blocks[0]
    heading = " ".join(first_block[4].split())

    return heading





def get_section_info(heading):
    """Parse a numbered heading if present; otherwise preserve it as plain text."""
    match = re.match(r"^\s*(\d+)\s*[·.)]\s*(.+?)\s*$", heading.replace("\n", " "))
    if match:
        return int(match.group(1)), match.group(2).strip()
    return None, heading.strip()


def extract_raw_tables():
    """Create raw tables only once; do not overwrite an existing raw extraction."""
    if RAW_TABLES.exists():
        print(f"Raw table file already exists; preserving it: {RAW_TABLES}")
        return read_json(RAW_TABLES)
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    raw_tables = []
    with pymupdf.open(PDF_PATH) as document:
        for page in document:
            for table_index, table in enumerate(find_tables(page), start=1):
                rows = [
                    [extract_cell_text(page, cell) for cell in table_row.cells]
                    for table_row in table.rows
                ]
                raw_tables.append({
                    "page": page.number + 1,
                    "table_index": table_index,
                    "bbox": list(table.bbox),
                    "row_count": table.row_count,
                    "col_count": table.col_count,
                    "heading_raw": page_heading(page, table.bbox),
                    "cells": rows,
                })

    write_json(RAW_TABLES, raw_tables)
    print(f"Created raw table file: {RAW_TABLES} ({len(raw_tables)} tables)")
    print("Raw table file will not be overwritten by this script.")
    return raw_tables


def join_cell_lines(text, location, audit, break_reviews):
    """
    Flatten a cell to one line. Join punctuation-only fragments without a space;
    join other non-empty fragments with a space. Log each decision for review.
    """
    original_lines = text.splitlines()
    nonempty = [(index, line) for index, line in enumerate(original_lines) if line.strip()]
    if not nonempty:
        if text:
            audit.append({
                **location, "change_type": "EMPTY_CELL_WHITESPACE",
                "original": repr(text), "cleaned": "''",
                "note": "Cell contained only whitespace or line breaks",
            })
        return ""

    result = nonempty[0][1].strip()
    for (before_index, before_line), (after_index, after_line) in zip(nonempty, nonempty[1:]):
        left, right = before_line.strip(), after_line.strip()
        if right and all(char in PUNCTUATION_ONLY for char in right):
            separator, decision = "", "JOIN_NO_SPACE"
            reason = "next non-empty fragment contains only punctuation/whitespace"
        else:
            separator, decision = " ", "JOIN_WITH_SPACE"
            reason = "conservative default; verify against the table image"

        result += separator + right
        break_reviews.append({
            **location,
            "line_before": before_index,
            "line_after": after_index,
            "left_fragment": left,
            "right_fragment": right,
            "proposed_decision": decision,
            "reason": reason,
        })
        audit.append({
            **location, "change_type": "CELL_LINE_BREAK",
            "original": f"{left} ⏎ {right}",
            "cleaned": f"{left}{separator}{right}",
            "note": reason,
        })

    if text != result and "\n" not in text and "\r" not in text:
        audit.append({
            **location, "change_type": "TRIM_WHITESPACE",
            "original": repr(text), "cleaned": repr(result),
            "note": "Removed leading/trailing whitespace",
        })
    return result


def clean_tables(raw_tables):
    cleaned_tables, audit, break_reviews = [], [], []

    for table in raw_tables:
        table_location = {"page": table["page"], "table_index": table["table_index"]}
        page_number = table["page"]

        with pymupdf.open(PDF_PATH) as document:
            page = document[page_number - 1]
            raw_heading = page_heading(page, table["bbox"])

        normalized_heading = rule_a(raw_heading)

        if normalized_heading != raw_heading:
            audit.append({
                **table_location, "row_index": "heading", "col_index": "",
                "change_type": "RULE_A", "original": repr(raw_heading),
                "cleaned": repr(normalized_heading),
                "note": "Unicode NFC and/or adjacent duplicate vowel-sign removal",
            })

        heading = join_cell_lines(
            normalized_heading,
            {**table_location, "row_index": "heading", "col_index": ""},
            audit, break_reviews,
        )
        section_no, section_title = get_section_info(heading)

        cleaned_rows = []
        for row_index, row in enumerate(table["cells"]):
            cleaned_row = []
            for col_index, raw_cell in enumerate(row):
                original = raw_cell if isinstance(raw_cell, str) else ""
                normalized = rule_a(original)
                location = {
                    **table_location, "row_index": row_index, "col_index": col_index,
                }
                if normalized != original:
                    audit.append({
                        **location, "change_type": "RULE_A",
                        "original": repr(original), "cleaned": repr(normalized),
                        "note": "Unicode NFC and/or adjacent duplicate vowel-sign removal",
                    })
                cleaned_row.append(join_cell_lines(normalized, location, audit, break_reviews))
            cleaned_rows.append(cleaned_row)

        cleaned_tables.append({
            **{key: value for key, value in table.items() if key not in ("cells", "heading_raw")},
            "section_no": section_no,
            "section_title": section_title,
            "cells": cleaned_rows,
        })

    write_json(CLEAN_TABLES, cleaned_tables)
    audit_fields = [
        "page", "table_index", "row_index", "col_index",
        "change_type", "original", "cleaned", "note",
    ]
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audit)

    review_fields = [
        "page", "table_index", "row_index", "col_index", "line_before", "line_after",
        "left_fragment", "right_fragment", "proposed_decision", "reason",
    ]
    with BREAKS_REVIEW_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=review_fields)
        writer.writeheader()
        writer.writerows(break_reviews)

    print(f"Clean tables saved: {CLEAN_TABLES}")
    print(f"Audit saved: {AUDIT_FILE} ({len(audit)} entries)")
    print(f"Cell line-break review saved: {BREAKS_REVIEW_FILE} ({len(break_reviews)} joins)")
    return cleaned_tables, audit


def build_rows(cleaned_tables):
    """Build one retrieval record per data row and a separate whole-table display file."""
    records, display_tables = [], []

    for table in cleaned_tables:
        rows = table["cells"]
        if not rows:
            continue

        # Assumption: the first row is the header. Confirm against the PDF image.
        header, data_rows = rows[0], rows[1:]
        table_id = f"p{table['page']}_t{table['table_index']}"

        display_tables.append({
            "table_id": table_id,
            "page": table["page"],
            "section_no": table["section_no"],
            "section_title": table["section_title"],
            "header": header,
            "rows": data_rows,
        })

        for row_index, row in enumerate(data_rows, start=1):
            parts = []
            for column_index, cell in enumerate(row):
                if column_index >= len(header):
                    continue
                if not cell.strip() or cell.strip() in ("—", "-"):
                    continue
                parts.append(f"{header[column_index]}: {cell}")

            text = " | ".join(part for part in [table["section_title"], *parts] if part.strip())
            records.append({
                "chunk_id": f"table_{table_id}_r{row_index}",
                "type": "table_row",
                "page": table["page"],
                "section_no": table["section_no"],
                "section_title": table["section_title"],
                "table_id": table_id,
                "row_index": row_index,
                "headers": header,
                "cells": row,
                "text": text,
            })

    write_json(ROWS_FILE, records)
    write_json(DISPLAY_FILE, display_tables)
    print(f"Row records saved: {ROWS_FILE} ({len(records)} records)")
    print(f"Display tables saved: {DISPLAY_FILE}")
    return records


def extract_prose_outside_tables():
    """
    Save text blocks outside table rectangles. Print every dropped block because
    a mixed prose/table block could otherwise lose prose text.
    Existing raw prose output is preserved on reruns.
    """
    if RAW_PROSE.exists():
        print(f"Raw table-page prose already exists; preserving it: {RAW_PROSE}")
        return read_json(RAW_PROSE)
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    output_pages = []
    with pymupdf.open(PDF_PATH) as document:
        for page in document:
            tables = find_tables(page)
            if not tables:
                continue

            kept, dropped = [], []
            blocks = [block for block in page.get_text("blocks") if block[6] == 0]
            blocks.sort(key=lambda block: (round(block[1]), block[0]))

            for block in blocks:
                rect = pymupdf.Rect(block[:4])
                if any(rect.intersects(pymupdf.Rect(table.bbox)) for table in tables):
                    dropped.append(block[4])
                else:
                    kept.append(block[4])

            print(f"\nPDF page {page.number + 1}: kept {len(kept)} blocks; "
                  f"dropped {len(dropped)} intersecting blocks")
            for text in dropped:
                print(f"  DROPPED BLOCK: {text!r}")

            output_pages.append({
                "page": page.number + 1,
                "text": "\n".join(block.strip() for block in kept if block.strip()),
            })

    write_json(RAW_PROSE, output_pages)
    print(f"Raw table-page prose saved: {RAW_PROSE}")
    print("Check dropped blocks for mixed prose/table content before using this output.")
    return output_pages


def report(cleaned_tables, records):
    """Print structural and character-level checks; these do not prove semantic accuracy."""
    cells = [cell for table in cleaned_tables for row in table["cells"] for cell in row]
    repeated = sum(
        1 for cell in cells for left, right in zip(cell, cell[1:])
        if left == right and ord(left) in VOWEL_SIGNS
    )
    nul_count = sum("\x00" in cell for cell in cells)
    newline_count = sum("\n" in cell or "\r" in cell for cell in cells)
    empty_count = sum(cell == "" for cell in cells)
    years = sorted(set(re.findall(r"(?<!\d)\d{4}(?!\d)", " ".join(cells))))

    print("\n" + "=" * 72)
    print(f"Tables: {len(cleaned_tables)} | Rows including headers: "
          f"{sum(len(t['cells']) for t in cleaned_tables)} | Data-row records: {len(records)}")

    for table in cleaned_tables:
        rows = table["cells"]
        columns = max((len(row) for row in rows), default=0)
        print(f"\nPDF page {table['page']} | table {table['table_index']} | "
              f"{len(rows)} rows x {columns} columns | section: {table['section_title']!r}")
        for row_index, row in enumerate(rows):
            print(f"  row {row_index}: {row!r}")

    print("\nAutomated checks (not proof of semantic correctness):")
    print(f"  Cells containing NUL: {nul_count}")
    print(f"  Cells containing line breaks: {newline_count}")
    print(f"  Adjacent duplicate vowel signs remaining: {repeated}")
    print(f"  Empty cells: {empty_count}")
    print(f"  Four-digit numbers found: {years}")
    print("Compare each cleaned cell against the PDF image before using it for RAG.")


def main():
    raw_tables = extract_raw_tables()
    cleaned_tables, _ = clean_tables(raw_tables)
    records = build_rows(cleaned_tables)
    print("\nProse extraction from table pages:")
    extract_prose_outside_tables()
    report(cleaned_tables, records)


if __name__ == "__main__":
    main()
