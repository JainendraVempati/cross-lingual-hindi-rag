import json
import re
import unicodedata
from pathlib import Path

from Extract_Raw_Pages import OUTPUT_DIR, SELECTED_PAGES, compare_results


INPUT_DIR = OUTPUT_DIR


def normalize_text(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def preprocess_pages(input_dir):
    for file_path in input_dir.glob("*.json"):
        if file_path.name == "comparison_report.json":
            continue

        with open(file_path, "r", encoding="utf-8") as file:
            pages = json.load(file)

        for page in pages:
            page["text"] = normalize_text(page.get("text", ""))

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(pages, file, ensure_ascii=False, indent=2)

        print(f"Normalized and saved: {file_path.name}")
        print(f"Pages processed: {len(pages)}")



preprocess_pages(INPUT_DIR)
print("\nComparing normalized extraction results")
compare_results(INPUT_DIR)


#Null characters are present in pypdf.json and pdfplumber.json, so first we are going to calculate total null charactrs and add them and then check total sum
null_counts = {}
for file_name in  ["pypdf.json", "pdfplumber.json"]:
    file_path = INPUT_DIR / file_name
    with open(file_path, "r", encoding="utf-8") as file:
        pages = json.load(file)

    total_null_count = sum(page.get("text", "").count("\x00") for page in pages)
    null_counts[file_name] = total_null_count
    print(f"{file_name}: {total_null_count} null characters")

combined_total = sum(null_counts.values())
print(f"\Combined null character count: {combined_total}")

if null_counts["pypdf.json"] == null_counts["pdfplumber.json"]:
    print("Both files have the same number of null characters.")
else:
    print("The null character counts differ between the files.")
