from pathlib import Path
import json
import unicodedata

PROJECT_DIR = Path(__file__).resolve().parent
INPUT_PATH = PROJECT_DIR / "artifacts" / "raw_pages.json"
OUTPUT_PATH = PROJECT_DIR / "artifacts" / "clean_pages.json"

EXPECTED_PAGES = 22


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


def normalize_whitespace_preserving_lines(text):
    cleaned_lines = []

    for line in text.splitlines():
        line = line.replace("\t", " ")
        line = " ".join(line.split())
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def apply_page_corrections(page_number, text):
    correction_count = 0

    if page_number == 7:
        old = "पूर्वर्ती"
        new = "पूर्ववर्ती"

        correction_count = text.count(old)
        text = text.replace(old, new)

        if correction_count != 1:
            raise ValueError(
                f"Page 7: expected 1 correction for {old!r}, "
                f"found {correction_count}."
            )

    elif page_number == 14:
        old = "पूर्वर्त"
        new = "पूर्ववर्त"

        correction_count = text.count(old)
        text = text.replace(old, new)

        if correction_count != 1:
            raise ValueError(
                f"Page 14: expected 1 correction for {old!r}, "
                f"found {correction_count}."
            )

    return text, correction_count


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Raw extraction not found: {INPUT_PATH}. Run extract.py first."
        )

    with INPUT_PATH.open("r", encoding="utf-8") as file:
        pages = json.load(file)

    if len(pages) != EXPECTED_PAGES:
        raise ValueError(
            f"Expected {EXPECTED_PAGES} pages, found {len(pages)}."
        )

    cleaned_pages = []
    total_corrections = 0

    for index, page in enumerate(pages):
        expected_page_number = index + 1

        if page.get("page_number") != expected_page_number:
            raise ValueError(
                f"Expected page number {expected_page_number}, "
                f"found {page.get('page_number')}."
            )

        text = unicodedata.normalize("NFC", page["text"])
        text = collapse_repeated_mark_sequences(text)
        text = normalize_whitespace_preserving_lines(text)

        text, correction_count = apply_page_corrections(
            expected_page_number, text
        )
        total_corrections += correction_count

        cleaned_pages.append({
            "page_number": expected_page_number,
            "text": text
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(cleaned_pages, file, ensure_ascii=False, indent=2)

    print(f"Cleaned {len(cleaned_pages)} pages.")
    print(f"Page-specific corrections applied: {total_corrections}")
    print(f"Saved cleaned text to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()