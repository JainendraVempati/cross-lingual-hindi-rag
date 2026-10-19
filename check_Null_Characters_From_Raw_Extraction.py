import json
from pathlib import Path
from difflib import SequenceMatcher
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "verification" / "raw_pages"


with open(RAW_DIR / "pymupdf.json", "r", encoding="utf-8") as file:
    pymupdf_pages = {item["page"]: item["text"]for item in json.load(file)}


with open(RAW_DIR / "pdfplumber.json", "r", encoding="utf-8") as file:
    pdfplumber_pages = {item["page"]: item["text"] for item in json.load(file)}

replacement_counts = Counter()


for page_number in [3, 4, 8]:
    pymupdf_text = pymupdf_pages[page_number]
    pdfplumber_text = pdfplumber_pages[page_number]

    matcher = SequenceMatcher(None,pymupdf_text,pdfplumber_text,autojunk=False)

    print(f"PAGE {page_number} :")

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        pdfplumber_part = pdfplumber_text[j1:j2]

        if "\x00" in pdfplumber_part:
            pymupdf_part = pymupdf_text[i1:i2]

            replacement_counts[pymupdf_part] += pdfplumber_part.count("\x00")

            print(f"\nPyMuPDF text:   {pymupdf_part!r}")
            print(f"pdfplumber text: {pdfplumber_part!r}")
            print("Context:",repr(pdfplumber_text[max(0, j1 - 15):min(len(pdfplumber_text), j2 + 15)]))


print("\nTop 10 candidate replacement strings:")

for text, count in replacement_counts.most_common(10):
    print(f"{text!r}: {count}")