
import json
import unicodedata
from collections import Counter
from pathlib import Path


# Project paths
BASE_DIR = Path(__file__).resolve().parent

RAW_FILE = (BASE_DIR/ "verification"/ "raw_pages"/ "pymupdf_raw.json")

PROCESSED_DIR = BASE_DIR / "data" / "processed"


# Dependent vowel signs:
# U+093E through U+094C, plus U+0962 and U+0963.
# Halant U+094D is excluded.
VOWEL_SIGNS = set(range(0x093E, 0x094D)) | {0x0962,0x0963,}


# Test words used to verify Rule A
TEST_WORDS = [
    "अक्टूबर",
    "द्वीप",
    "विज्ञान",
    "वैज्ञानिक",
    "स्कूल",
    "स्नेहपूर्ण",
    "स्रोत",
    "अब्दुल",
]


# Load the original raw extraction, This function only reads the file.
def load_raw_pages():
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Raw extraction file not found: {RAW_FILE}"
        )

    with RAW_FILE.open("r", encoding="utf-8") as file:
        pages = json.load(file)

    print("Raw extraction loaded.")
    print(f"Pages loaded: {len(pages)}")

    return pages


# Rule A: collapse adjacent identical vowel signs. The raw pages are not modified.
def apply_rule_a(pages):
    cleaned_pages = []
    audit = []
    counts = Counter()

    for page in pages:
        original = page["text"]
        result = []
        i = 0

        while i < len(original):
            char = original[i]

            if (i + 1 < len(original)and char == original[i + 1]and ord(char) in VOWEL_SIGNS):
                result.append(char)

                audit.append({
                    "page": page["page"],
                    "before": char + char,
                    "after": char,
                    "codepoint": f"U+{ord(char):04X}",
                    "name": unicodedata.name(
                        char, "UNKNOWN"
                    ),
                    "context": original[
                        max(0, i - 12):i + 14
                    ],
                })

                counts[f"U+{ord(char):04X}"] += 1

                # Skip both copies after retaining one.
                i += 2

            else:
                result.append(char)
                i += 1

        cleaned_pages.append({**page,"text": "".join(result),})

    print("\nRule A summary")
    print(f"Changes made: {len(audit)}")

    for codepoint, count in sorted(counts.items()):
        print(f"{codepoint}: {count}")

    return cleaned_pages, audit


# Verify expected words in the cleaned pages.
def verify_cleaned_words(pages, words):
    print("\nRule A word verification")

    for word in words:
        found_pages = [page["page"] for page in pages if word in page["text"]]

        if found_pages:
            print(
                f"FOUND: {word} | Pages: {found_pages}"
            )
        else:
            print(f"NOT FOUND: {word}")


# Save the cleaned output and audit log separately.
def save_rule_a_outputs(cleaned_pages, audit):
    PROCESSED_DIR.mkdir(parents=True,exist_ok=True,)

    cleaned_file = (PROCESSED_DIR / "pymupdf_rule_a_cleaned.json")

    audit_file = PROCESSED_DIR / "rule_a_audit.json"

    with cleaned_file.open("w", encoding="utf-8") as file:
        json.dump(cleaned_pages,file,ensure_ascii=False,indent=2,)

    with audit_file.open("w", encoding="utf-8") as file:
        json.dump(audit,file,ensure_ascii=False,indent=2,)

    print("\nRule A files saved:")
    print(cleaned_file)
    print(audit_file)


# Main execution
def main():
    pages = load_raw_pages()
    cleaned_pages, audit = apply_rule_a(pages)
    verify_cleaned_words(cleaned_pages,TEST_WORDS,)
    save_rule_a_outputs(cleaned_pages,audit,)


if __name__ == "__main__":
    main()
