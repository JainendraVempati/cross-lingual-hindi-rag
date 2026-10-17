from pathlib import Path
import json
import pymupdf

PROJECT_DIR = Path(__file__).resolve().parent
PDF_PATH = PROJECT_DIR / "data" / "Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf"
OUTPUT_PATH = PROJECT_DIR / "artifacts" / "raw_pages.json"
EXPECTED_PAGES = 22


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    pages = []

    with pymupdf.open(PDF_PATH) as document:
        if len(document) != EXPECTED_PAGES:
            raise ValueError(
                f"Expected {EXPECTED_PAGES} pages, found {len(document)}."
            )

        for index, page in enumerate(document):
            pages.append({
                "page_number": index + 1,
                "text": page.get_text("text", sort=False)
            })

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(pages, file, ensure_ascii=False, indent=2)

    print(f"Extracted {len(pages)} pages.")
    print(f"Saved raw extraction to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()