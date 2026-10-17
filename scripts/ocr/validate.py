from pathlib import Path
import difflib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata

PROJECT_DIR = Path(__file__).resolve().parent
PDF_PATH = PROJECT_DIR / "data" / "Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf"
CLEAN_PATH = PROJECT_DIR / "artifacts" / "clean_pages.json"

EXPECTED_PAGES = 22
PAGE_ONE_HYPHEN_EXCEPTION = "रिट्रीवल-ऑगमेंटेड"


def normalize_for_comparison(text):
    text = unicodedata.normalize("NFC", text)
    return "".join(text.split())


def apply_known_comparison_exception(text, page_number):
    if page_number == 1:
        return text.replace(PAGE_ONE_HYPHEN_EXCEPTION, "रिट्रीवलऑगमेंटेड")
    return text


def find_adjacent_duplicate_marks(text):
    issues = []

    for index in range(1, len(text)):
        current = text[index]
        previous = text[index - 1]

        if (
            current == previous
            and unicodedata.category(current).startswith("M")
        ):
            issues.append((index - 1, previous, current))

    return issues


def print_differences(left, right, limit=8, context=25):
    matcher = difflib.SequenceMatcher(a=left, b=right, autojunk=False)
    shown = 0

    for tag, left_start, left_end, right_start, right_end in matcher.get_opcodes():
        if tag == "equal":
            continue

        shown += 1

        left_fragment = left[left_start:left_end]
        right_fragment = right[right_start:right_end]

        left_context = left[
            max(0, left_start - context):
            min(len(left), left_end + context)
        ]
        right_context = right[
            max(0, right_start - context):
            min(len(right), right_end + context)
        ]

        print(f"    Difference type: {tag}")
        print(f"    Clean range: {left_start}:{left_end}")
        print(f"    Poppler range: {right_start}:{right_end}")
        print(f"    Clean text: {left_fragment!r}")
        print(f"    Poppler text: {right_fragment!r}")
        print(f"    Clean code points: {[f'U+{ord(c):04X}' for c in left_fragment]}")
        print(f"    Poppler code points: {[f'U+{ord(c):04X}' for c in right_fragment]}")
        print(f"    Clean context: {left_context!r}")
        print(f"    Poppler context: {right_context!r}")

        if shown >= limit:
            break


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    if not CLEAN_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned text not found: {CLEAN_PATH}. Run clean.py first."
        )

    pdftotext = shutil.which("pdftotext")

    if pdftotext is None:
        raise FileNotFoundError(
            "pdftotext was not found on PATH. Install Poppler or add it to PATH."
        )

    with CLEAN_PATH.open("r", encoding="utf-8") as file:
        clean_pages = json.load(file)

    if len(clean_pages) != EXPECTED_PAGES:
        raise ValueError(
            f"Expected {EXPECTED_PAGES} cleaned pages, found {len(clean_pages)}."
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "poppler.txt"

        subprocess.run(
            [
                pdftotext,
                "-enc", "UTF-8",
                str(PDF_PATH),
                str(output_path)
            ],
            check=True
        )

        poppler_text = output_path.read_text(encoding="utf-8")

    poppler_pages = poppler_text.split("\f")

    while poppler_pages and not poppler_pages[-1].strip():
        poppler_pages.pop()

    if len(poppler_pages) != EXPECTED_PAGES:
        raise ValueError(
            f"Poppler returned {len(poppler_pages)} pages; "
            f"expected {EXPECTED_PAGES}."
        )

    passed = 0
    failed = 0
    digit_mismatches = 0
    duplicate_mark_issues = 0

    print("PAGE VALIDATION")
    print("-" * 70)

    for index in range(EXPECTED_PAGES):
        page_number = index + 1
        page = clean_pages[index]

        if page.get("page_number") != page_number:
            raise ValueError(
                f"Page order error: expected page {page_number}, "
                f"found {page.get('page_number')}."
            )

        clean_raw = unicodedata.normalize("NFC", page["text"])
        poppler_raw = unicodedata.normalize("NFC", poppler_pages[index])

        duplicate_marks = find_adjacent_duplicate_marks(clean_raw)

        if duplicate_marks:
            duplicate_mark_issues += len(duplicate_marks)
            print(
                f"Page {page_number}: WARNING - "
                f"{len(duplicate_marks)} adjacent duplicate combining marks"
            )

            for position, first, second in duplicate_marks[:5]:
                print(
                    f"    Position {position}: "
                    f"{first!r} U+{ord(first):04X}, "
                    f"{second!r} U+{ord(second):04X}"
                )

        clean_digits = re.findall(r"\d+", clean_raw)
        poppler_digits = re.findall(r"\d+", poppler_raw)

        if clean_digits != poppler_digits:
            digit_mismatches += 1
            print(f"Page {page_number}: DIGIT SEQUENCE MISMATCH")
            print(f"    Clean digits: {clean_digits}")
            print(f"    Poppler digits: {poppler_digits}")

        clean_compare = normalize_for_comparison(clean_raw)
        poppler_compare = normalize_for_comparison(poppler_raw)

        clean_compare = apply_known_comparison_exception(
            clean_compare, page_number
        )
        poppler_compare = apply_known_comparison_exception(
            poppler_compare, page_number
        )

        if clean_compare == poppler_compare:
            passed += 1
            print(f"Page {page_number:2}: PASS")
        else:
            failed += 1
            print(
                f"Page {page_number:2}: MISMATCH "
                f"(clean={len(clean_compare)}, Poppler={len(poppler_compare)})"
            )
            print_differences(clean_compare, poppler_compare)

    print("-" * 70)
    print(f"Passed: {passed}/{EXPECTED_PAGES}")
    print(f"Mismatched: {failed}/{EXPECTED_PAGES}")
    print(f"Pages with digit-sequence mismatches: {digit_mismatches}")
    print(f"Adjacent duplicate combining-mark issues: {duplicate_mark_issues}")

    if failed or digit_mismatches or duplicate_mark_issues:
        print("Validation needs review before proceeding.")
    else:
        print("All validation checks passed.")


if __name__ == "__main__":
    main()