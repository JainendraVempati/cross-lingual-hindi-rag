#We want to check whether PyMuPDF extracts Hindi text correctly from your PDF.

import json
import pymupdf
from pathlib import Path
import re
import unicodedata
import unicodedata
from collections import Counter, defaultdict

# Step 1: Define paths
BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    BASE_DIR
    / "verification"
    / "raw_pages"
    / "pymupdf.json"
)

# PRIORITY 1: Required query answers (prose pages)
TEST_WORDS = [
    # Q1 â€” Page 8
    "à¤°à¥‹à¤¹à¤¿à¤£à¥€",
    "SLV-III",
    "à¤œà¥à¤²à¤¾à¤ˆ 1980",

    # Q3 â€” Page 10
    "à¤ªà¥‹à¤–à¤°à¤£-II",
    "à¤¡à¥€à¤†à¤°à¤¡à¥€à¤“",

    # Q4 â€” Page 6
    "à¤®à¤¦à¥à¤°à¤¾à¤¸ à¤‡à¤‚à¤¸à¥à¤Ÿà¥€à¤Ÿà¥à¤¯à¥‚à¤Ÿ à¤‘à¤« à¤Ÿà¥‡à¤•à¥à¤¨à¥‹à¤²à¥‰à¤œà¥€",

    # Q5 â€” Page 3
    "à¤…à¤°à¥à¤£ à¤¤à¤¿à¤µà¤¾à¤°à¥€",
    "1999",

    # Q6 â€” Page 15
    "à¤¶à¤¿à¤²à¤¾à¤‚à¤—",
    "27 à¤œà¥à¤²à¤¾à¤ˆ 2015",
    "83 à¤µà¤°à¥à¤·",

    # PRIORITY 2: Dates in prose
    # Pages 3, 4, 8, 10, 14, 15
    "1931",
    "15 à¤…à¤•à¥à¤Ÿà¥‚à¤¬à¤° 1931",
    "1979",
    "1980",
    "à¤®à¤ˆ 1998",
    "2002",
    "2007",
    "2015",
    "2020",
    "1930 à¤•à¥‡ à¤¦à¤¶à¤•",
    "1950 à¤•à¥‡ à¤¦à¤¶à¤•",

    # PRIORITY 2: People
    "à¤•à¤²à¤¾à¤®",
    "à¤œà¥ˆà¤¨à¥à¤²à¤¾à¤¬à¤¦à¥€à¤¨",
    "à¤†à¤¶à¤¿à¤…à¤®à¥à¤®à¤¾",
    "à¤µà¤¿à¤•à¥à¤°à¤® à¤¸à¤¾à¤°à¤¾à¤­à¤¾à¤ˆ",
    "à¤¸à¤¤à¥€à¤¶ à¤§à¤µà¤¨",
    "à¤†à¤¯à¤¡à¥à¤°à¤ˆ à¤¸à¥‹à¤²à¥‹à¤®à¤¨",
    "à¤…à¤µà¥à¤²",

    # PRIORITY 2: Places and institutions
    "à¤°à¤¾à¤®à¥‡à¤¶à¥à¤µà¤°à¤®",
    "à¤¤à¤®à¤¿à¤²à¤¨à¤¾à¤¡à¥",
    "à¤ªà¤®à¥à¤¬à¤¨",
    "à¤°à¤¾à¤®à¤¨à¤¾à¤¥à¤ªà¥à¤°à¤®",
    "à¤¶à¥à¤µà¤¾à¤°à¥à¤Ÿà¥à¤œà¤¼",
    "à¤¤à¤¿à¤°à¥à¤šà¤¿à¤°à¤¾à¤ªà¤²à¥à¤²à¥€",
    "à¤¸à¥‡à¤‚à¤Ÿ à¤œà¥‹à¤¸à¥‡à¤« à¤•à¥‰à¤²à¥‡à¤œ",
    "à¤šà¥‡à¤¨à¥à¤¨à¤ˆ",
    "à¤¹à¤¿à¤¨à¥à¤¦à¥à¤¸à¥à¤¤à¤¾à¤¨ à¤à¤¯à¤°à¥‹à¤¨à¥‰à¤Ÿà¤¿à¤•à¥à¤¸",
    "à¤‡à¤¸à¤°à¥‹",
    "à¤°à¤¾à¤œà¤¸à¥à¤¥à¤¾à¤¨",
    "à¤‘à¤ªà¤°à¥‡à¤¶à¤¨ à¤¶à¤•à¥à¤¤à¤¿",
    "à¤°à¤¾à¤·à¥à¤Ÿà¥à¤°à¤ªà¤¤à¤¿ à¤­à¤µà¤¨",
    "à¤®à¥‡à¤˜à¤¾à¤²à¤¯",
    "à¤­à¤¾à¤°à¤¤à¥€à¤¯ à¤ªà¥à¤°à¤¬à¤‚à¤§à¤¨ à¤¸à¤‚à¤¸à¥à¤¥à¤¾à¤¨",

    # PRIORITY 3: Additional technical terms in prose
    "à¤¦à¤•à¥à¤·à¤¿à¤£-à¤ªà¥‚à¤°à¥à¤µà¥€",
    "à¤†à¤¤à¥à¤®à¤¨à¤¿à¤°à¥à¤­à¤°à¤¤à¤¾",
    "à¤ªà¤°à¤¿à¤¶à¥à¤°à¤®",
    "à¤‡à¤‚à¤œà¥€à¤¨à¤¿à¤¯à¤°à¤¿à¤‚à¤—",
    "à¤µà¤¿à¤œà¥à¤žà¤¾à¤¨",
    "à¤ªà¤°à¤¿à¤¸à¥à¤¥à¤¿à¤¤à¤¿à¤¯à¥‹à¤‚",
    "à¤‰à¤¨à¥à¤¹à¥‹à¤‚à¤¨à¥‡",
    "à¤µà¤¿à¤«à¤²à¤¤à¤¾",
    "à¤¸à¥à¤¥à¤¿à¤¤",
    "à¤®à¥à¤¸à¥à¤²à¤¿à¤®",
    "à¤…à¤•à¥à¤Ÿà¥‚à¤¬à¤°",
    "à¤¦à¥à¤µà¥€à¤ª",
]




# Step 1: Define paths
BASE_DIR = Path(__file__).resolve().parent
PDF_FILE = (BASE_DIR/ "data"/ "Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf")
RAW_FILE = (BASE_DIR/ "verification"/ "raw_pages"/ "pymupdf_raw.json")

# Pages to extract (PDF page numbers start at 1)
SELECTED_PAGES = [3, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 18, 19]


# Step 2: Extract raw text from the PDF
def extract_raw_pages():
    RAW_FILE.parent.mkdir(parents=True, exist_ok=True)

    results = []

    with pymupdf.open(PDF_FILE) as doc:
        for page_number in SELECTED_PAGES:
            page = doc[page_number - 1]

            results.append({"page": page_number,"text": page.get_text("text")})

    with open(RAW_FILE, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    print(f"Raw extraction saved: {RAW_FILE}")
    print(f"Pages extracted: {len(results)}")


# Step 3: Load and inspect the saved raw text
def load_raw_pages():
    with open(RAW_FILE, "r", encoding="utf-8") as file:
        pages = json.load(file)

    print("\nRaw PyMuPDF Extraction Check")
    print(f"Pages loaded: {len(pages)}")

    for page in pages:
        print(f"Page {page['page']}: "f"{len(page['text'])} characters")
    return pages





#Using one by one Function
def check_extracted_words(pages):
    print("\nHindi Word Verification â€” Raw Extraction")

    for word in TEST_WORDS:
        normal_found_pages = []
        whitespace_ignored_pages = []

        word_without_whitespace = re.sub(r"\s+", "", word)

        for page in pages:
            page_number = page["page"]
            text = page["text"]

            if word in text:
                normal_found_pages.append(page_number)

            text_without_whitespace = re.sub(r"\s+", "", text)

            if word_without_whitespace in text_without_whitespace:
                whitespace_ignored_pages.append(page_number)

        if normal_found_pages:
            print(f"FOUND NORMALLY: {word} | "f"Pages: {normal_found_pages}")
        elif whitespace_ignored_pages:
            print(f"FOUND ONLY AFTER IGNORING WHITESPACE: "f"{word} | Pages: {whitespace_ignored_pages}")
        else:
            print(f"NOT FOUND: {word}")





import unicodedata
import regex


import unicodedata
import regex


def inspect_invisible_characters(pages):
    pattern = regex.compile(r"[\p{Default_Ignorable_Code_Point}\p{Cc}\p{Zl}\p{Zp}\u00A0]")

    found = {}

    for page in pages:
        text = page["text"]

        for match in pattern.finditer(text):
            char = match.group()

            if char in "\n\r\t":
                continue

            codepoint = ord(char)
            name = unicodedata.name(char, "UNKNOWN")
            category = unicodedata.category(char)
            key = (codepoint, name, category)

            if key not in found:
                found[key] = {"count": 0, "pages": set()}

            found[key]["count"] += 1
            found[key]["pages"].add(page["page"])

    print("\nInvisible Character Inventory")

    if not found:
        print("No suspicious characters detected.")
        return

    for (codepoint, name, category), info in sorted(found.items()):
        print(f"U+{codepoint:04X} | {name} | Category: {category} | "f"Count: {info['count']} | Pages: {sorted(info['pages'])}")





def step_remove_invisible_characters(pages):
    cleaned_pages = []

    for page in pages:
        cleaned_text = "".join(
            char for char in page["text"]
            if char in "\n\r\t" or char.isprintable()
        )

        cleaned_pages.append({
            **page,
            "text": cleaned_text
        })

    return cleaned_pages



def step_nfc(pages):
    cleaned_pages = []

    for page in pages:
        cleaned_text = unicodedata.normalize("NFC", page["text"])
        cleaned_pages.append({**page,"text": cleaned_text})

    return cleaned_pages





def test_nfc(pages, nfc_pages):
    for original, normalized in zip(pages, nfc_pages):
        if original["text"] != normalized["text"]:
            print(f"Page {original['page']}: Unicode representation changed")

    print("Raw pages:", len(pages))
    print("Normalized pages:", len(nfc_pages))
    print("Raw file remains unchanged.")






def inspect_whitespace(pages):
    print("\Whitespace Inspection")


    total_issues = 0

    for page in pages:
        text = page["text"]
        page_issues = []

        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.startswith((" ", "\t")):
                page_issues.append((line_number, "Leading whitespace", repr(line[:80])))

            if line.endswith((" ", "\t")):
                page_issues.append((line_number, "Trailing whitespace", repr(line[-80:])))

            if "  " in line:
                page_issues.append((line_number, "Repeated spaces", repr(line[:120])))

            if "\t" in line:
                page_issues.append(
                    (line_number, "Tab character", repr(line[:120]))
                )

        newline_count = text.count("\n")
        empty_lines = sum(1 for line in text.splitlines()if not line.strip())

        if page_issues or empty_lines:
            print(f"\nPage {page['page']}:")
            total_issues += len(page_issues)

            for line_number, issue, context in page_issues:
                print(f"  Line {line_number}: {issue} | {context}")

            if empty_lines:
                print(f"  Empty lines: {empty_lines}")

        print(f"  Line breaks: {newline_count} | "f"Empty lines: {empty_lines}")

    print("\nInspection complete.")
    print(f"Reported line-level issues: {total_issues}")
    print("No text was modified.")



import re
import unicodedata


def inspect_word_structure(pages):
    print("\nWord-Level Structure Inspection")

    # A line break between two parts of a Devanagari word
    split_pattern = re.compile(r"([\u0900-\u097F]+)[ \t]*\n[ \t]*([\u0900-\u097F]+)")

    for page in pages:
        text = page["text"]
        findings = []

        for match in split_pattern.finditer(text):
            left = match.group(1)
            right = match.group(2)

            # Report possible splits, not confirmed errors.
            findings.append({"type": "Possible word split across newline","position": match.start(),"text": repr(match.group(0))})

        if findings:
            print(f"\nPage {page['page']}:")

            for finding in findings:
                print(f"  {finding['type']} | "f"Position: {finding['position']} | "f"Text: {finding['text']}")

    print("\nInspection complete.")
    print("All findings require verification against the PDF.")
    print("No text was modified.")








import unicodedata


def inspect_word_codepoints(word):
    print(f"\nWord: {word}")
    for char in word:
        print(f"{char} -> U+{ord(char):04X} "f"({unicodedata.name(char, 'UNKNOWN')})")








def inspect_repeated_combining_marks(pages):
    counts = Counter()
    examples = defaultdict(list)

    for page in pages:
        text = page["text"]

        for i in range(len(text) - 1):
            current = text[i]
            following = text[i + 1]

            if (current == following and unicodedata.category(current) in ("Mn", "Mc")):
                name = unicodedata.name(current, "UNKNOWN")
                key = (ord(current), name)

                counts[key] += 1

                if len(examples[key]) < 10:
                    examples[key].append({"page": page["page"],"context": text[max(0, i - 8):i + 10]})

    if not counts:
        print("No repeated combining marks found.")
        return

    print("\nRepeated combining marks:")

    for (codepoint, name), count in sorted(counts.items()):
        print(f"U+{codepoint:04X} {name}: {count} occurrences")

        for item in examples[(codepoint, name)]:
            print(f"  Page {item['page']}: "f"{item['context']!r}")









VOWEL_SIGNS = set(range(0x093E, 0x094D)) | {0x0962, 0x0963}
def inspect_duplicate_vowel_signs(pages):
    counts = Counter()
    examples = defaultdict(list)

    for page in pages:
        text = page["text"]

        for i in range(len(text) - 1):
            char = text[i]

            if char == text[i + 1] and ord(char) in VOWEL_SIGNS:
                counts[ord(char)] += 1

                if len(examples[ord(char)]) < 5:
                    examples[ord(char)].append((page["page"], text[max(0, i - 10):i + 12]))

    print("\nDuplicate vowel-sign report")

    for codepoint, count in sorted(counts.items()):
        name = unicodedata.name(chr(codepoint), "UNKNOWN")
        print(f"\nU+{codepoint:04X} {name}: {count}")

        for page_number, context in examples[codepoint]:
            print(f"  Page {page_number}: {context!r}")

    if not counts:
        print("No duplicate vowel signs found.")








def inspect_page_context(pages, page_number, search_text):
    for page in pages:
        if page["page"] == page_number:
            text = page["text"]
            position = text.find(search_text)

            if position == -1:
                print(f"Not found on page {page_number}: {search_text}")
                return

            print(f"\nPage {page_number}:")
            print(repr(text[max(0, position - 30):position + 70]))
            return

    print(f"Page {page_number} is not loaded.")
