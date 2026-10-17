
from pathlib import Path
import json
import re
import unicodedata
import pymupdf

PROJECT_DIR = Path(__file__).resolve().parent

PDF_PATH = PROJECT_DIR / "data" / "Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf"
CLEAN_PATH = PROJECT_DIR / "artifacts" / "clean_pages.json"
OUTPUT_PATH = PROJECT_DIR / "artifacts" / "tables.json"

EXPECTED_TABLES = {
    9: 6,
    12: 6,
    16: 6,
    17: 14,
    20: 10,
    22: 13,
}


def collapse_repeated_mark_sequences(text):
    result = []
    index = 0

    while index < len(text):
        if not unicodedata.category(text[index]).startswith("M"):
            result.append(text[index])
            index += 1
            continue

        end = index

        while (
            end < len(text)
            and unicodedata.category(text[end]).startswith("M")
        ):
            end += 1

        marks = text[index:end]

        deduplicated = []
        for mark in marks:
            if not deduplicated or mark != deduplicated[-1]:
                deduplicated.append(mark)

        marks = "".join(deduplicated)

        for period in range(1, len(marks) // 2 + 1):
            if len(marks) % period == 0:
                pattern = marks[:period]

                if pattern * (len(marks) // period) == marks:
                    marks = pattern
                    break

        result.append(marks)
        index = end

    return "".join(result)


def clean_cell(text):
    text = unicodedata.normalize("NFC", text)
    text = collapse_repeated_mark_sequences(text)

    lines = [
        " ".join(line.replace("\t", " ").split())
        for line in text.splitlines()
    ]

    lines = [line for line in lines if line]

    if not lines:
        return ""

    joined = lines[0]

    for line in lines[1:]:
        if joined.endswith(("-", "‐")):
            joined += line
        else:
            joined += " " + line

    joined = re.sub(r"\s+([,.;:!?।)])", r"\1", joined)

    return joined.strip()

def normalize_for_match(text):
    text = unicodedata.normalize("NFC", text)
    return "".join(text.split())


def get_cell_text(page, cell_box):
    if cell_box is None:
        return ""

    rectangle = pymupdf.Rect(cell_box)
    raw_text = page.get_textbox(rectangle)
    return clean_cell(raw_text)


def extract_table_from_boxes(page, table):
    extracted_rows = []

    for row in table.rows:
        extracted_row = []

        for cell_box in row.cells:
            extracted_row.append(get_cell_text(page, cell_box))

        extracted_rows.append(extracted_row)

    return extracted_rows


def find_expected_table(page, page_number, expected_rows):
    finder = page.find_tables()
    tables = finder.tables

    print(
        f"Page {page_number}: "
        f"{len(tables)} table(s) detected automatically"
    )

    for table in tables:
        print(
            f"  Detected table: "
            f"{table.row_count} rows x {table.col_count} columns"
        )

    matching = [
        table for table in tables
        if table.row_count == expected_rows
    ]

    if matching:
        return matching[0]

    if tables:
        largest = max(tables, key=lambda table: table.row_count)
        print(
            f"  WARNING: expected {expected_rows} rows, "
            f"but no detected table has that row count."
        )
        return largest

    print("  ERROR: no table detected on this page.")
    return None


def check_required_rows(all_tables):
    checks = [
        {
            "name": "1997 — Bharat Ratna",
            "page": 17,
            "terms": ["1997", "भारत रत्न"],
        },
        {
            "name": "1980 — Rohini satellite",
            "page": 17,
            "terms": ["1980", "रोहिणी"],
        },
        {
            "name": "1998 — Pokhran-II",
            "page": 17,
            "terms": ["1998", "पोखरण-II"],
        },
        {
            "name": "1999 — Arun Tiwari",
            "page": 17,
            "terms": ["1999", "अरुण तिवारी"],
        },
        {
            "name": "Page 22 — autobiography",
            "page": 22,
            "terms": ["आत्मकथा"],
        },
    ]

    print("\nREQUIRED CONTENT CHECKS")
    print("-" * 60)

    failed = 0

    for check in checks:
        page_number = check["page"]
        terms = check["terms"]

        page_tables = [
            table for table in all_tables
            if table["page_number"] == page_number
        ]

        matching_rows = []

        for table in page_tables:
            for row in table["rows"]:
                row_text = normalize_for_match(" ".join(row))
                if all(
                    normalize_for_match(term) in row_text
                    for term in terms
                ):
                    matching_rows.append(row)

        if matching_rows:
            print(f"PASS: {check['name']}")
            print(f"  Row: {' | '.join(matching_rows[0])}")
        else:
            failed += 1
            print(f"FAIL: {check['name']}")

    return failed


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if not CLEAN_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned text not found: {CLEAN_PATH}"
        )

    with CLEAN_PATH.open("r", encoding="utf-8") as file:
        clean_pages = json.load(file)

    clean_by_page = {
        item["page_number"]: item["text"]
        for item in clean_pages
    }

    all_tables = []
    table_detection_errors = 0
    newline_errors = 0
    cell_membership_errors = 0
    row_count_errors = 0

    with pymupdf.open(PDF_PATH) as document:
        if len(document) != 22:
            raise ValueError(
                f"Expected 22 PDF pages; found {len(document)}."
            )

        for page_number, expected_rows in EXPECTED_TABLES.items():
            page = document[page_number - 1]

            table = find_expected_table(
                page, page_number, expected_rows
            )

            if table is None:
                table_detection_errors += 1
                continue

            rows = extract_table_from_boxes(page, table)

            if len(rows) != expected_rows:
                row_count_errors += 1
                print(
                    f"  ROW COUNT MISMATCH: expected {expected_rows}, "
                    f"extracted {len(rows)}"
                )

            cleaned_page = normalize_for_match(
                clean_by_page.get(page_number, "")
            )

            for row_index, row in enumerate(rows, start=1):
                for column_index, cell in enumerate(row, start=1):
                    if "\n" in cell or "\r" in cell:
                        newline_errors += 1
                        print(
                            f"  NEWLINE ERROR: page {page_number}, "
                            f"row {row_index}, column {column_index}"
                        )

                    if cell:
                        normalized_cell = normalize_for_match(cell)

                        if normalized_cell not in cleaned_page:
                            cell_membership_errors += 1
                            print(
                                f"  CELL NOT FOUND IN CLEANED PAGE: "
                                f"page {page_number}, "
                                f"row {row_index}, column {column_index}"
                            )
                            print(f"    Cell: {cell!r}")

            all_tables.append({
                "page_number": page_number,
                "row_count": len(rows),
                "column_count": table.col_count,
                "rows": rows,
            })

            print(
                f"  Extracted {len(rows)} rows "
                f"and {table.col_count} columns."
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open(
        "w", encoding="utf-8", newline="\n"
    ) as file:
        json.dump(
            all_tables,
            file,
            ensure_ascii=False,
            indent=2
        )

    required_row_errors = check_required_rows(all_tables)

    print("\nFINAL TABLE VALIDATION")
    print("-" * 60)
    print(f"Expected tables: {len(EXPECTED_TABLES)}")
    print(f"Extracted tables: {len(all_tables)}")
    print(f"Table detection errors: {table_detection_errors}")
    print(f"Row-count errors: {row_count_errors}")
    print(f"Cells containing newlines: {newline_errors}")
    print(f"Cells missing from cleaned page text: {cell_membership_errors}")
    print(f"Required content check failures: {required_row_errors}")
    print(f"Saved tables to: {OUTPUT_PATH}")

    if (
        len(all_tables) != len(EXPECTED_TABLES)
        or table_detection_errors
        or row_count_errors
        or newline_errors
        or cell_membership_errors
        or required_row_errors
    ):
        print("\nRESULT: REVIEW REQUIRED — do not proceed to chunking yet.")
    else:
        print("\nRESULT: ALL TABLE CHECKS PASSED.")


if __name__ == "__main__":
    main()
