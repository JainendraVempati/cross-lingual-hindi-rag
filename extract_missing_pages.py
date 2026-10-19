import json
import pymupdf
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PDF = ROOT / "data" / "Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf"
OUTPUT = ROOT / "verification" / "raw_pages" / "pymupdf_raw_missing_pages.json"

if OUTPUT.exists():
    raise SystemExit(f"STOP: refusing to overwrite {OUTPUT}")

if not PDF.exists():
    raise SystemExit(f"PDF not found: {PDF}")

pages = []

with pymupdf.open(PDF) as doc:
    if len(doc) != 22:
        raise SystemExit(f"Expected 22 pages, found {len(doc)}")

    for page_no in (1, 2, 21):
        text = doc[page_no - 1].get_text("text").strip()
        pages.append({"page": page_no, "text": text})

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(pages, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

for page in pages:
    print(f"Page {page['page']}: {len(page['text'])} characters")
    print(page["text"][:200].replace("\n", " "))
    print()

print(f"Saved raw extraction: {OUTPUT}")
print("Existing raw files were not modified.")
