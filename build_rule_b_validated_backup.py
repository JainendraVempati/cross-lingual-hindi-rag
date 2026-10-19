"""
Rule B with conservative structural preservation.

- No Hindi vocabulary/function-word dictionary.
- Generic boundary proposals do not use known joins.
- Known joins are only validation examples.
- Preserves recognized section/subheadings and bullet/list items as separate lines.
- Unresolved word-split candidates default to a space.
- Does not modify raw extraction or Rule A output.

Run:
    $env:PYTHONUTF8="1"
    python build_rule_b.py build
    # Inspect the review CSV; final_decision is prefilled only for the 18
    # explicitly PDF-verified word joins.
    python build_rule_b.py apply
    python build_rule_b.py check
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROCESSED = BASE / "data" / "processed"
INPUT = PROCESSED / "pymupdf_rule_a_cleaned.json"
REVIEW_CSV = PROCESSED / "rule_b_manual_review.csv"
OUTPUT = PROCESSED / "clean_pages_AB.json"
AUDIT = PROCESSED / "audit_rule_b.csv"

SENTENCE_END = "।॥?!"
PUNCT = " \t.,;:!?()[]{}\"'“”‘’–—-।॥"
HEADING = re.compile(r"^\s*(\d+)\s*[·.]\s*(.+?)\s*$")
BULLET = re.compile(r"^\s*[•●▪◦]\s*")
VALID = {"KEEP_NEWLINE", "JOIN_NO_SPACE", "JOIN_WITH_SPACE", "REVIEW"}

# These are exact document structure labels observed in the source PDF,
# not a general Hindi vocabulary or dictionary.
STRUCTURAL_HEADINGS = {
    4: {"इस नगर ने उन्हें क्या दिया"},
    11: {
        "सपने: उपलब्धि का इंजन",
        "विफलता: शिक्षक, निर्णय नहीं",
        "विज्ञान और अध्यात्म साथ-साथ",
        "राष्ट्र: एक साझा परियोजना",
    },
}

# PDF-verified joins used as explicit correction decisions and validation cases.
# They are not fed into the generic classifier.
KNOWN_JOINS = {
    (4, "स्थि", "त"),
    (4, "मुस्लि", "म"),
    (8, "व्यक्ति", "गत"),
    (8, "परिस्थि", "तियों"),
    (10, "स्थि", "ति"),
    (11, "व्यक्ति", "गत"),  # occurs three times on page 11
    (11, "निष्क्रि", "य"),
    (11, "व्यक्ति", "यों"),
    (11, "स्थि", "रता"),
    (11, "शक्ति", "याँ"),
    (13, "उपस्थि", "ति"),
    (13, "उपस्थि", "त"),
    (13, "व्यक्ति", "गत"),
    (14, "पंक्ति", "यों"),
    (15, "स्थि", "र"),
    (18, "व्यक्ति", "गत"),
}

FIELDS = [
    "id", "page", "line_idx", "line_before", "left", "right", "line_after",
    "leading_space", "left_last_char", "left_ends_sentence", "right_only_punct",
    "proposed_decision", "tier", "evidence", "verified", "final_decision", "note",
]


def load_pages():
    if not INPUT.exists():
        sys.exit(f"Input file not found: {INPUT}")
    with INPUT.open(encoding="utf-8") as f:
        pages = json.load(f)
    if not isinstance(pages, list):
        sys.exit("Input JSON must be a list of objects containing 'page' and 'text'.")
    for i, p in enumerate(pages, 1):
        if not isinstance(p, dict) or "page" not in p or not isinstance(p.get("text"), str):
            sys.exit(f"Invalid JSON item {i}: expected page and text.")
    return pages


def split_heading(text):
    """
    Extract section heading. Supports a heading broken over two physical lines
    when the first line is exactly a section-number/title prefix and the next
    line starts with the continuation 'की उड़ान के मुख्य विषय'.
    """
    lines = text.split("\n")
    first_nonempty = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_nonempty is None:
        return None, None, text

    m = HEADING.match(lines[first_nonempty])
    if not m:
        return None, None, text

    section_no, title = int(m.group(1)), m.group(2).strip()
    body_start = first_nonempty + 1

    # Document-specific layout repair: this PDF's page 11 heading wraps after "अग्नि".
    if (section_no == 9 and title == "अग्नि" and body_start < len(lines)
            and lines[body_start].strip() == "की उड़ान के मुख्य विषय"):
        title = "अग्नि की उड़ान के मुख्य विषय"
        body_start += 1

    return section_no, title, "\n".join(lines[body_start:])


def classify(before, after):
    left_line, right_line = before.strip(), after.strip()
    left_frag, right_frag = left_line.split()[-1], right_line.split()[0]
    core = left_line.rstrip("”’\"')")
    info = {
        "left": left_frag,
        "right": right_frag,
        "leading_space": after[:1] in (" ", "\t"),
        "left_last_char": left_line[-1],
        "left_ends_sentence": bool(core) and core[-1] in SENTENCE_END,
        "right_only_punct": bool(right_frag) and all(c in PUNCT for c in right_frag),
    }
    if info["left_ends_sentence"]:
        tier, decision, evidence = 0, "KEEP_NEWLINE", "left line ends in sentence punctuation"
    elif info["right_only_punct"]:
        tier, decision, evidence = 1, "JOIN_NO_SPACE", "right fragment contains only punctuation"
    elif info["leading_space"]:
        tier, decision, evidence = 2, "JOIN_WITH_SPACE", "next physical line starts with whitespace"
    elif info["left_last_char"] != "ि":
        tier, decision, evidence = 3, "JOIN_WITH_SPACE", "left line does not end in ि"
    else:
        tier, decision, evidence = 5, "REVIEW", "possible split word; inspect PDF"
    info.update(tier=tier, proposed_decision=decision, evidence=evidence)
    return info


def known_join_occurrences(rows):
    return [r for r in rows if r["verified"] == "true"]


def build():
    rows = []
    for p in load_pages():
        page_no = int(p["page"])
        _, _, body = split_heading(p["text"])
        lines = body.split("\n")
        for i in range(len(lines) - 1):
            before, after = lines[i], lines[i + 1]
            if not before.strip() or not after.strip():
                continue
            info = classify(before, after)
            key = (page_no, info["left"].strip(PUNCT), info["right"].strip(PUNCT))
            verified = key in KNOWN_JOINS
            rows.append({
                "id": len(rows) + 1,
                "page": page_no,
                "line_idx": i,
                "line_before": before.strip()[-100:],
                "left": info["left"],
                "right": info["right"],
                "line_after": after.strip()[:100],
                "leading_space": str(info["leading_space"]).lower(),
                "left_last_char": info["left_last_char"],
                "left_ends_sentence": str(info["left_ends_sentence"]).lower(),
                "right_only_punct": str(info["right_only_punct"]).lower(),
                "proposed_decision": info["proposed_decision"],
                "tier": info["tier"],
                "evidence": info["evidence"],
                "verified": "true" if verified else "",
                "final_decision": "JOIN_NO_SPACE" if verified else "",
                "note": "PDF-verified validation example" if verified else "",
            })

    known = known_join_occurrences(rows)
    known_i = sum(r["left_last_char"] == "ि" for r in known)
    known_leading = sum(r["leading_space"] == "true" for r in known)
    lead = [r for r in rows if r["leading_space"] == "true"]
    review = sum(r["tier"] == 5 and r["verified"] != "true" for r in rows)

    print(f"Boundaries: {len(rows)}")
    print("Rows per tier:", dict(sorted(Counter(int(r["tier"]) for r in rows).items())))
    print(f"Known joins matched: {len(known)} (expected 18)")
    print(f"Test 1: known joins with left ending in ि: {known_i}/{len(known)}")
    print(f"Test 2: known joins with leading whitespace: {known_leading} (expected 0)")
    print(f"Test 3: other ि-ending boundaries: "
          f"{sum(r['left_last_char'] == 'ि' and r['verified'] != 'true' for r in rows)}")
    print(f"Test 4: leading-space boundaries to inspect: {len(lead)}")
    for r in lead:
        print(f"  page {r['page']}: {r['left']} | {r['right']}")
    print(f"Unverified Tier 5 boundaries needing review: {review}")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved review CSV: {REVIEW_CSV}")
    failures = []
    if len(known) != 18:
        failures.append(f"expected 18 known join occurrences; found {len(known)}")
    if known_i != len(known):
        failures.append("not all known joins have left fragments ending in ि")
    if known_leading:
        failures.append("known join has a leading-space flag")
    if review > 40:
        failures.append(f"{review} unresolved Tier 5 cases exceed the review limit of 40")
    if failures:
        print("SAFETY TESTS FAILED — do not run apply:")
        for item in failures:
            print(f" - {item}")
        sys.exit(2)
    print("Critical tests passed. Review the CSV before running apply.")


def apply():
    if not REVIEW_CSV.exists():
        sys.exit(f"Review CSV not found: {REVIEW_CSV}. Run build first.")

    decisions = {}
    with REVIEW_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"page", "line_idx", "proposed_decision", "final_decision"}
        if not required.issubset(set(reader.fieldnames or [])):
            sys.exit(f"CSV is missing required columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            try:
                key = (int(row["page"]), int(row["line_idx"]))
            except (TypeError, ValueError):
                sys.exit(f"Invalid page/line_idx in CSV row {row.get('id', '?')}")
            final = (row.get("final_decision") or "").strip()
            proposed = (row.get("proposed_decision") or "").strip()
            decision = final or proposed
            if decision not in VALID:
                sys.exit(f"Row {row.get('id', '?')}: invalid decision {decision!r}")
            decisions[key] = (decision, "final" if final else "proposed")

    glue = {"KEEP_NEWLINE": "\n", "JOIN_NO_SPACE": "", "JOIN_WITH_SPACE": " "}
    output_pages, audit = [], []

    for p in load_pages():
        page_no = int(p["page"])
        section_no, section_title, body = split_heading(p["text"])
        lines = body.split("\n")  # Keep physical line indices aligned with the review CSV.
        result = []
        i = 0

        def clean(line):
            return line.strip()

        def is_list_item(line):
            x = clean(line)
            return bool(BULLET.match(x)) or (
                page_no == 4 and x.startswith((
                    "संकीर्णता रहित आस्था", "ईमानदार श्रम का सम्मान",
                    "आकाश और समुद्र के प्रति जिज्ञासा"
                ))
            )

        def is_heading(line):
            return clean(line) in STRUCTURAL_HEADINGS.get(page_no, set())

        def add_newline():
            while result and result[-1] == "":
                result.pop()
            if result and result[-1] != "\n":
                result.append("\n")

        while i < len(lines):
            raw = lines[i]
            line = clean(raw)
            if not line:
                add_newline()
                i += 1
                continue

            # The subheading is split across two physical lines in the source extraction.
            # Reconstruct it from the adjacent layout lines, not from a word dictionary.
            if (page_no == 11 and line == "सपने: उपलब्धि"
                    and i + 1 < len(lines) and clean(lines[i + 1]) == "का इंजन"):
                add_newline()
                result.extend(["सपने: उपलब्धि का इंजन", "\n"])
                audit.append({"page": page_no, "line_idx": i, "decision": "KEEP_HEADING",
                              "source": "structural_layout", "left": line,
                              "right": clean(lines[i + 1]),
                              "note": "wrapped heading reconstructed from adjacent physical lines"})
                i += 2
                continue

            if is_heading(line):
                add_newline()
                result.extend([line, "\n"])
                audit.append({"page": page_no, "line_idx": i, "decision": "KEEP_HEADING",
                              "source": "structural_layout", "left": "", "right": line,
                              "note": "heading preserved on its own line"})
                i += 1
                continue

            if is_list_item(line):
                add_newline()
                item = line
                start_i = i
                i += 1
                # A list item may wrap onto following physical lines. Join its continuation
                # with the same general boundary decision, stopping before another item,
                # heading, blank line, or a clear sentence-ending boundary.
                while i < len(lines) and clean(lines[i]):
                    nxt = clean(lines[i])
                    if is_list_item(nxt) or is_heading(nxt):
                        break
                    decision, source = decisions.get((page_no, i - 1), ("JOIN_WITH_SPACE", "default"))
                    if decision == "KEEP_NEWLINE":
                        break
                    if decision == "REVIEW":
                        decision, source = "JOIN_WITH_SPACE", "unresolved_default"
                    item += glue[decision] + nxt
                    audit.append({"page": page_no, "line_idx": i - 1, "decision": decision,
                                  "source": source, "left": clean(lines[i - 1]).split()[-1],
                                  "right": nxt.split()[0], "note": "list-item continuation"})
                    i += 1
                    if item.endswith(("।", "॥", "?", "!")):
                        break
                result.extend([item, "\n"])
                audit.append({"page": page_no, "line_idx": start_i, "decision": "KEEP_LIST_ITEM",
                              "source": "structural_layout", "left": "", "right": item,
                              "note": "list item preserved as a separate logical line"})
                continue

            # Build one logical run, consulting the decision for the exact physical
            # boundary index. Do not skip/reuse indices after a join.
            run = line
            start_i = i
            preserved_boundary = False
            while i + 1 < len(lines) and clean(lines[i + 1]):
                nxt = clean(lines[i + 1])
                if is_heading(nxt) or is_list_item(nxt):
                    break
                decision, source = decisions.get((page_no, i), ("JOIN_WITH_SPACE", "default"))
                if decision == "REVIEW":
                    decision, source = "JOIN_WITH_SPACE", "unresolved_default"
                if decision == "KEEP_NEWLINE":
                    audit.append({"page": page_no, "line_idx": i, "decision": decision,
                                  "source": source, "left": clean(lines[i]).split()[-1],
                                  "right": nxt.split()[0], "note": "preserved physical line boundary"})
                    preserved_boundary = True
                    break
                run += glue[decision] + nxt
                audit.append({"page": page_no, "line_idx": i, "decision": decision,
                              "source": source, "left": clean(lines[i]).split()[-1],
                              "right": nxt.split()[0], "note": "joined using boundary decision"})
                i += 1
            result.append(run)
            if preserved_boundary:
                result.append("\n")
            # If stopped at a preserved boundary, consume only the left line; otherwise
            # i already points at the last line included in the run.
            i += 1

        text = "".join(result).strip()
        # Normalize only accidental repeated newline markers, not text content.
        text = re.sub(r"\n{3,}", "\n\n", text)
        output_pages.append({**p, "section_no": section_no, "section_title": section_title, "text": text})

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(output_pages, f, ensure_ascii=False, indent=2)
    with AUDIT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "line_idx", "decision", "source", "left", "right", "note"])
        writer.writeheader()
        writer.writerows(audit)
    print(f"Saved output: {OUTPUT}")
    print(f"Saved audit: {AUDIT}")
    print("Decision sources:", dict(Counter(r["source"] for r in audit)))
    print("Decision types:", dict(Counter(r["decision"] for r in audit)))


JOINED = [
    "स्थित", "मुस्लिम", "व्यक्तिगत", "परिस्थितियों", "स्थिति", "निष्क्रिय",
    "व्यक्तियों", "स्थिरता", "शक्तियाँ", "उपस्थिति", "उपस्थित", "पंक्तियों", "स्थिर",
]
SPACES = ["ऑपरेशन शक्ति", "बल्कि शक्ति", "व्यक्ति थे।"]
WORDS = [
    "अक्टूबर", "तमिलनाडु", "द्वीप", "दक्षिण-पूर्वी", "आत्मनिर्भरता", "परिश्रम",
    "इंजीनियरिंग", "विज्ञान", "रोहिणी", "उन्होंने", "विफलता",
]
FUSED = ["वालेएक", "सकताहै", "छपतीऔर", "जुड़ावऔपचारिक", "हुएहैं"]
MOJIBAKE = ["Ã", "à¤", "â€"]


def check():
    if not OUTPUT.exists():
        sys.exit(f"Output not found: {OUTPUT}. Run apply first.")
    with OUTPUT.open(encoding="utf-8") as f:
        pages = json.load(f)
    full = "\n".join(p.get("text", "") for p in pages)
    page19 = "\n".join(p.get("text", "") for p in pages if int(p.get("page", -1)) == 19)

    def report(title, items):
        print(f"\n{title}")
        for item in items:
            print(f"  {'FOUND    ' if item in full else 'NOT FOUND'}  {item}")

    report("Joined-word checks", JOINED)
    report("Required-space checks", SPACES)
    report("Search-word checks (presence only)", WORDS)
    print("\nFused-string counts (whole text / page 19)")
    for item in FUSED:
        print(f"  {item}: {full.count(item)} / {page19.count(item)}")
    print("\nMojibake marker counts")
    for marker in MOJIBAKE:
        print(f"  {marker!r}: {full.count(marker)}")
    print("\nSpacing regression checks")
    spacing_checks = [
        (11, "जो मायने रखता है वह है प्रतिक्रिया"),
        (11, "निर्णय नहीं, बल्कि जानकारी मानती है"),
        (14, "यद्यपि राष्ट्रपति का पद"),
        (15, "सार्वजनिक व्यक्ति को मिलता है"),
    ]
    for page_no, phrase in spacing_checks:
        p = next((x for x in pages if int(x["page"]) == page_no), None)
        found = bool(p and phrase in p.get("text", ""))
        print(f"  {'PASS    ' if found else 'CHECK   '} page {page_no}: {phrase}")

    print("\nStructural checks")
    for page_no, heading in [
        (4, "इस नगर ने उन्हें क्या दिया"),
        (11, "सपने: उपलब्धि का इंजन"),
        (11, "विफलता: शिक्षक, निर्णय नहीं"),
        (11, "विज्ञान और अध्यात्म साथ-साथ"),
        (11, "राष्ट्र: एक साझा परियोजना"),
    ]:
        p = next((x for x in pages if int(x["page"]) == page_no), None)
        found = bool(p and heading in p["text"])
        print(f"  {'FOUND    ' if found else 'NOT FOUND'} page {page_no}: {heading}")
    print("\nManual validation still required: compare output against the PDF images.")


if __name__ == "__main__":
    modes = {"build": build, "apply": apply, "check": check}
    if len(sys.argv) != 2 or sys.argv[1] not in modes:
        sys.exit("Usage: python build_rule_b.py build|apply|check")
    modes[sys.argv[1]]()
