
import argparse
import csv
import json
import re
from pathlib import Path



BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "processed" / "pymupdf_rule_a_cleaned.json"
OUTPUT_DIR = BASE_DIR / "data" / "processed"
REVIEW_FILE = OUTPUT_DIR / "rule_b_manual_review_experiment.csv"
AUDIT_FILE = OUTPUT_DIR / "audit_rule_b_experiment.csv"
OUTPUT_FILE = OUTPUT_DIR / "clean_pages_B_experiment.json"



DEVANAGARI_LETTER = re.compile(r"[\u0900-\u0939\u0958-\u0961]")
DEVANAGARI_MARK = re.compile(r"[\u093a-\u094f\u0951-\u0957\u0962-\u0963]")
PUNCTUATION_ONLY = re.compile(r"^[\sà¥¤à¥¥,;:!?\.â€¦)\]}\"'â€™â€]+$")

SENTENCE_ENDINGS = ("à¥¤", "à¥¥", "?", "!", "â€¦", ".")

BULLET_PREFIXES = ("â€¢","â—","â—‹","â–ª","â–«","â– ","â–¡","â€“","â€”",)


def is_devanagari_char(char):
    if not char:
        return False
    return bool(DEVANAGARI_LETTER.fullmatch(char)or DEVANAGARI_MARK.fullmatch(char))


def is_sentence_ending(text):
    return text.rstrip().endswith(SENTENCE_ENDINGS)


def is_bullet_line(text):
    stripped = text.lstrip()

    return any(stripped.startswith(prefix)for prefix in BULLET_PREFIXES)







def is_heading_like(text):
    """
    Conservative, document-independent heading heuristic.
    Recognizes numbered headings and short title-like lines.
    """
    stripped = text.strip()

    if not stripped or len(stripped) > 90:
        return False

    if is_sentence_ending(stripped):
        return False

    words = stripped.split()

    if len(words) > 12:
        return False

    # Numbered section headings, e.g. "9 Â· à¤…à¤—à¥à¤¨à¤¿ à¤•à¥€ à¤‰à¤¡à¤¼à¤¾à¤¨ à¤•à¥‡ à¤®à¥à¤–à¥à¤¯ à¤µà¤¿à¤·à¤¯"
    if re.match(r"^\d+\s*[Â·.)]\s+\S+", stripped):
        return True

    # Short title-like lines with no sentence-ending punctuation.
    return len(words) <= 8




def classify_boundary(left, right):
    """
    Conservative, document-independent boundary classification.

    Never joins suspected Hindi word fragments automatically.
    """

    left = left.rstrip()
    right = right.lstrip()

    if not left:
        return "JOIN_WITH_SPACE", "Empty left line"

    if not right:
        return "JOIN_WITH_SPACE", "Empty right line"

    if is_bullet_line(right):
        return "KEEP_NEWLINE", "New line starts with a bullet"

    # Preserve a numbered section heading on the left.
    if re.match(r"^\d+\s*[Â·.)]\s+\S+", left.strip()):
        return "KEEP_NEWLINE", "Numbered section heading"

        # Attach punctuation-only lines to preceding text.
    if PUNCTUATION_ONLY.fullmatch(right):
        return "JOIN_NO_SPACE", "Right line contains punctuation only"

    # Preserve clear sentence boundaries.
    if is_sentence_ending(left):
        return "KEEP_NEWLINE", "Left line ends with sentence punctuation"



    # Default to a space rather than guessing a word join.
    return "JOIN_WITH_SPACE", "Conservative default"







def load_pages():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Input JSON must contain a list of page records.")

    seen_pages = set()

    for record in data:
        if not isinstance(record, dict):
            raise ValueError("Every page record must be a JSON object.")

        if "page" not in record or "text" not in record:
            raise ValueError("Every page record must contain 'page' and 'text'.")

        if not isinstance(record["text"], str):
            raise ValueError(f"Page {record['page']} has non-string text.")

        page_number = record["page"]

        if page_number in seen_pages:
            raise ValueError(f"Duplicate page number found: {page_number}")
        seen_pages.add(page_number)

    return data





def build():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pages = load_pages()
    rows = []

    for record in pages:
        page_number = record["page"]
        lines = record["text"].splitlines()

        boundary_index = 0

        for line_index in range(len(lines) - 1):
            left = lines[line_index]
            right = lines[line_index + 1]

            # Empty lines are retained as paragraph boundaries.
            if not left.strip() or not right.strip():
                continue

            proposed, reason = classify_boundary(left, right)

            rows.append({
                "page": page_number,
                "boundary_index": boundary_index,
                "left_line": left,
                "right_line": right,
                "proposed_decision": proposed,
                "reason": reason,
                "final_decision": "",
            })

            boundary_index += 1

    fieldnames = [
        "page",
        "boundary_index",
        "left_line",
        "right_line",
        "proposed_decision",
        "reason",
        "final_decision",
    ]

    with REVIEW_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    decision_counts = {}

    for row in rows:
        decision = row["proposed_decision"]
        decision_counts[decision] = (
            decision_counts.get(decision, 0) + 1
        )

    print("Rule B review CSV created.")
    print(f"Input pages: {len(pages)}")
    print(f"Boundaries reviewed: {len(rows)}")
    print(f"Proposed decisions: {decision_counts}")
    print(f"Review file: {REVIEW_FILE}")




def apply():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pages = load_pages()

    if not REVIEW_FILE.exists():
        raise FileNotFoundError(f"Review CSV not found: {REVIEW_FILE}. Run build first.")

    decisions = {}

    with REVIEW_FILE.open("r",encoding="utf-8-sig",newline="") as file:
        reader = csv.DictReader(file)

        required_columns = {
            "page",
            "boundary_index",
            "left_line",
            "right_line",
            "proposed_decision",
            "final_decision",
        }

        if not required_columns.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                "Review CSV is missing required columns."
            )

        for row in reader:
            key = (int(row["page"]),int(row["boundary_index"]))

            if key in decisions:
                raise ValueError(f"Duplicate boundary entry in review CSV: {key}")

            final_decision = row["final_decision"].strip()
            proposed_decision = row["proposed_decision"].strip()

            allowed = {"JOIN_WITH_SPACE","JOIN_NO_SPACE","KEEP_NEWLINE","REVIEW",}

            if final_decision and final_decision not in allowed:
                raise ValueError(f"Invalid final decision {final_decision!r} "f"at boundary {key}")

            if final_decision:
                decision = final_decision
                source = "manual_review"
            elif proposed_decision == "REVIEW":
                decision = "JOIN_WITH_SPACE"
                source = "unresolved_default"
            else:
                decision = proposed_decision
                source = "proposed"

            decisions[key] = {
                "decision": decision,
                "source": source,
                "left_line": row["left_line"],
                "right_line": row["right_line"],
            }

    output_pages = []
    audit_rows = []
    used_keys = set()

    for record in pages:
        page_number = record["page"]
        lines = record["text"].splitlines()

        if not lines:
            output_pages.append({
                "page": page_number,
                "text": record["text"],
            })
            continue

        result = lines[0]

        boundary_index = 0

        for line_index in range(len(lines) - 1):
            left = lines[line_index]
            right = lines[line_index + 1]

            # Preserve blank lines as paragraph boundaries.
            if not left.strip() or not right.strip():
                result += "\n" + right
                continue

            key = (page_number, boundary_index)

            if key not in decisions:
                raise ValueError(f"Missing review decision for boundary {key}. ""Rebuild the review CSV.")

            item = decisions[key]
            decision = item["decision"]
            used_keys.add(key)

            # Guard against applying a stale CSV to changed input.
            if (item["left_line"] != left or item["right_line"] != right):
                raise ValueError(f"Review CSV text does not match input at {key}. ""Rebuild the review CSV before applying it.")

            if decision == "JOIN_WITH_SPACE":
                separator = " "
            elif decision == "JOIN_NO_SPACE":
                separator = ""
            elif decision == "KEEP_NEWLINE":
                separator = "\n"
            else:
                raise ValueError(f"Unsupported decision {decision!r} at {key}")

            result += separator + right

            audit_rows.append({
                "page": page_number,
                "boundary_index": boundary_index,
                "left_line": left,
                "right_line": right,
                "decision": decision,
                "decision_source": item["source"],
                "output_separator": repr(separator),
            })

            boundary_index += 1

        output_pages.append({"page": page_number,"text": result,})

    unused_keys = set(decisions) - used_keys

    if unused_keys:
        raise ValueError("Review CSV contains boundaries not present in the input. "f"Examples: {list(unused_keys)[:5]}. Rebuild the review CSV.")

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(output_pages,file,ensure_ascii=False,indent=2)

    audit_fields = [
        "page",
        "boundary_index",
        "left_line",
        "right_line",
        "decision",
        "decision_source",
        "output_separator",
    ]

    with AUDIT_FILE.open("w",encoding="utf-8-sig",newline="") as file:
        writer = csv.DictWriter(file, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audit_rows)

    source_counts = {}

    for row in audit_rows:
        source = row["decision_source"]
        source_counts[source] = source_counts.get(source, 0) + 1

    print("Experimental Rule B output created.")
    print(f"Pages processed: {len(output_pages)}")
    print(f"Boundaries applied: {len(audit_rows)}")
    print(f"Decision sources: {source_counts}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Audit: {AUDIT_FILE}")



def main():
    parser = argparse.ArgumentParser(description="Generic, conservative Rule B line-boundary processing.")

    parser.add_argument("mode",choices=["build", "apply", "all"],help="build review CSV, apply decisions, or run both")

    args = parser.parse_args()

    if args.mode in ("build", "all"):
        build()

    if args.mode in ("apply", "all"):
        apply()


if __name__ == "__main__":
    main()
