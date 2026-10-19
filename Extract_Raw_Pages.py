import json
import subprocess
from pathlib import Path
import fitz
import pdfplumber
from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parent
PDF_PATH = (PROJECT_ROOT/"data"/"Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf")
OUTPUT_DIR = Path(__file__).resolve().parent/"verification"/"raw_pages"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

#This file is used to extract pages which are not having any tables, so explicitly we are going to take only pages which are not having any tables
SELECTED_PAGES = [3, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 18]

def make_page_record(page_number, text):
    return {
        "page": page_number,
        "text": text or ""
    }


def extract_with_pymupdf(pdf_path, selected_pages):
    results = []

    with fitz.open(pdf_path) as document:
        for page_number in selected_pages:
            page = document[page_number - 1]
            text = page.get_text("text")

            results.append(make_page_record(page_number, text))
    return results



def extract_with_pdfplumber(pdf_path, selected_pages):
    results = []

    with pdfplumber.open(pdf_path) as document:
        for page_number in selected_pages:
            page = document.pages[page_number - 1]
            text = page.extract_text() or ""

            results.append(make_page_record(page_number, text))
    return results




def extract_with_pypdf(pdf_path, selected_pages):
    results = []

    reader = PdfReader(str(pdf_path))

    for page_number in selected_pages:
        page = reader.pages[page_number - 1]
        text = page.extract_text() or ""

        results.append(make_page_record(page_number, text))
    return results



def save_results(results, output_path):
    output_path.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Saved: {output_path}")
    print(f"Pages extracted: {len(results)}")



def compare_results(output_dir):
    files = {
        "PyMuPDF": output_dir / "pymupdf.json",
        "pdfplumber": output_dir / "pdfplumber.json",
        "pypdf": output_dir / "pypdf.json"
    }

    result = {}

    for library_name, file_path in files.items():
        with open(file_path, "r", encoding="utf-8") as file:
            pages = json.load(file)

        result[library_name] = {item["page"]: item["text"] for item in pages}
    #Now, we are going to compare Text equality, Text Length, Text differences

    for page_number in SELECTED_PAGES:
        pymupdf_text = result["PyMuPDF"].get(page_number, "")
        pdfplumber_text = result["pdfplumber"].get(page_number, "")
        pypdf_text = result["pypdf"].get(page_number, "")

        print(f"\nPage {page_number}")
        print("PyMuPDF:", len(pymupdf_text), "characters")
        print("pdfplumber:", len(pdfplumber_text), "characters")
        print("pypdf:", len(pypdf_text), "characters")

        if pymupdf_text == pdfplumber_text == pypdf_text:
            print(f"All three outputs are identical for page {page_number}.")
        else:
            print(f"Outputs differ in page {page_number}. Further inspection required.")








pymupdf_results = extract_with_pymupdf(PDF_PATH, SELECTED_PAGES)
save_results(pymupdf_results, OUTPUT_DIR / "pymupdf.json")

pdfplumber_results = extract_with_pdfplumber(PDF_PATH, SELECTED_PAGES)
save_results(pdfplumber_results, OUTPUT_DIR / "pdfplumber.json")

pypdf_results = extract_with_pypdf(PDF_PATH, SELECTED_PAGES)
save_results(pypdf_results, OUTPUT_DIR / "pypdf.json")


compare_results(OUTPUT_DIR)
