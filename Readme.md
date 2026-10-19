# Stage 1: PDF Text Extraction and Comparative Evaluation

## 1. Objective

Extract text page by page from the Hindi PDF using multiple libraries and compare their outputs to determine which method is most suitable for the RAG pipeline.

The PDF contains Hindi text, technical terms, and tables. Correct extraction is important because missing characters, fused words, incorrect reading order, and spacing errors can affect document chunking, retrieval quality, and answer generation.

The objective is to select a reliable extraction method before starting the cleaning, chunking, and embedding stages.

## 2. Extraction Methods

The following methods are being evaluated:

- **PyMuPDF:** Extracts PDF text page by page and provides access to word-level and character-level positions.
- **pdfplumber:** Extracts text and provides tools for examining character positions and tables.
- **pypdf:** Provides an alternative PDF text extraction implementation.
- **Poppler (`pdftotext`):** Planned as an additional independent extraction method.
- **Tesseract OCR:** Will be considered if ordinary text extraction is insufficient.

No extraction library was assumed to be the best before testing.

## 3. Work Completed

### Step 1: Select pages without tables

Selected 12 pages for the initial text extraction experiment:

`3, 4, 5, 6, 7, 8, 10, 11, 13, 14, 15, 18`

These pages were selected to evaluate ordinary text extraction separately from table extraction.

The table pages will be evaluated separately because tables require additional structural validation.

### Step 2: Extract text using three libraries

Created separate extraction functions for:

- PyMuPDF
- pdfplumber
- pypdf

Each extraction function processes the selected pages and stores the page number and extracted text in a list of records.

The extraction functions use the PDF page number to retrieve the corresponding page from each library.

### Step 3: Save extraction results

The extracted results were saved in separate JSON files:

- `pymupdf.json`
- `pdfplumber.json`
- `pypdf.json`

Each JSON file contains page records with the following fields:

- `page`: The PDF page number.
- `text`: The extracted text for that page.

Initially, the outputs were saved without text normalization or manual corrections.

### Step 4: Compare extracted text

Implemented a comparison function that loads the three JSON files and retrieves the text for the same page from each extractor.

The comparison reports:

- Character count for each extractor.
- Whether all three outputs are identical.
- Pages where the extracted texts differ.

This established that the three extraction methods produced different results and required further investigation.

### Step 5: Investigate null characters

During further inspection, null characters (`\x00`) were found in the pdfplumber and pypdf outputs.

Examples observed in the extracted text included:

- `\x00ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°`
- `ÃƒÂ Ã‚Â¤Ã‚Â®\x00`
- `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦\x00ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â°`
- `\x00ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¤`
- `ÃƒÂ Ã‚Â¤Ã‚Âª\x00ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â®`
- `\x00ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Âª`
- `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â°\x00\x00ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡`

These patterns indicate that the extracted Hindi text is damaged. The null characters occur in locations where Hindi vowel signs, conjuncts, or other characters may be missing.

The exact intended characters must be verified against the PDF itself rather than inferred from the null characters alone.

### Step 6: Normalize whitespace for comparison

Created a text normalization function using Unicode NFC normalization and Python regular expressions.

The function is:

```python
def normalize_text(text):
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
```

The function performs three operations:

1. Unicode NFC normalization.
2. Replacement of consecutive whitespace characters, including spaces, tabs, and newlines, with a single space.
3. Removal of leading and trailing whitespace.

This normalization makes whitespace differences easier to compare. However, it does not repair missing Hindi characters, recover null characters, or separate fused words.

**Important:** Normalization overwrites the JSON files if they are opened in write mode. Therefore, future raw extraction outputs must be kept separate from normalized outputs.

### Step 7: Investigate null-character replacements

Created a script named `check_Null_Characters_From_Raw_Extraction.py` to compare the PyMuPDF and pdfplumber outputs.

The script uses:

- `difflib.SequenceMatcher`
- `autojunk=False`
- Context surrounding differing text blocks
- `collections.Counter` to count candidate replacement strings

The initial investigation focused on pages 3, 4, and 8.

The purpose was to determine what PyMuPDF extracted in regions where pdfplumber contained null characters.

The comparison produced candidate fragments, but these are not confirmed replacements. The extraction libraries may place Hindi vowel signs in different logical or visual positions, so the character-level alignment can be misleading.

Consequently, replacing null characters directly with the corresponding PyMuPDF text is not considered a reliable repair method.

## 4. Initial Results

All three libraries returned text for the 12 selected pages.

| Page | PyMuPDF characters | pdfplumber characters | pypdf characters |
|---:|---:|---:|---:|
| 3 | 1,389 | 1,303 | 1,324 |
| 4 | 1,480 | 1,379 | 1,394 |
| 5 | 1,129 | 1,075 | 1,084 |
| 6 | 1,287 | 1,210 | 1,223 |
| 7 | 1,162 | 1,110 | 1,116 |
| 8 | 1,417 | 1,376 | 1,391 |
| 10 | 1,063 | 1,007 | 1,024 |
| 11 | 1,244 | 1,176 | 1,184 |
| 13 | 1,164 | 1,107 | 1,115 |
| 14 | 968 | 914 | 932 |
| 15 | 1,063 | 1,023 | 1,028 |
| 18 | 816 | 781 | 789 |

These character counts were recorded during the initial extraction experiment. They should not be treated as final counts after subsequent normalization or re-extraction.

## 5. Findings and Observations

### 5.1 Character-count differences

- PyMuPDF returned the highest character count on all 12 selected pages.
- pypdf returned more characters than pdfplumber on all 12 selected pages.
- The three extracted texts were not identical on any of the selected pages.
- Character-count differences alone do not establish extraction accuracy.

Differences may result from missing characters, spacing, line breaks, reading order, or other extraction behavior.

### 5.2 Null characters in pdfplumber and pypdf

The inspected outputs contain null characters in Hindi words. Some examples suggest missing vowel signs or conjuncts.

The current evidence indicates that pdfplumber and pypdf are unsuitable as the primary prose extraction methods for this document unless their text extraction problems can be resolved.

The null-character count and representative examples should be retained as evidence for the extraction evaluation and documented in the final project notes.

### 5.3 Limitations of the replacement comparison

The `SequenceMatcher` comparison produced candidate fragments, including empty strings and Hindi fragments such as `ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡`, `ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬`, `ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡`, `ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡`, and `ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡`.

These results cannot be interpreted as a verified replacement map.

Hindi vowel signs such as `ÃƒÂ Ã‚Â¤Ã‚Â¿` may appear visually before a consonant while being represented in Unicode logical order after it. As a result, the two extraction outputs may not align character by character.

**No automatic null-character replacement has been approved.**

### 5.4 Current extraction decision

PyMuPDF is the preferred candidate for prose extraction because its output appears more suitable for the next verification stage.

However, its correctness has not yet been fully established through visual verification. It must be checked directly against the PDF images, particularly for Hindi characters, conjuncts, and word spacing.

The extraction stage will be considered complete only after these checks pass.




The main goal is to verify whether PyMuPDF extracts Hindi text correctly from your PDF before we start cleaning the text for RAG.
    Imagine your original PDF contains this word:
        Original PDF : ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤
        But the extracted text might contain : ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ ÃƒÂ Ã‚Â¤Ã‚Â¤
    The PDF visually displays ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤, but PyMuPDF might extract it with a space in the middle.
    There are two possible explanations for a missing word:
        - Problem A ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Spacing problem: Every character is correct, but an unwanted space or line break splits the word.
        - Problem B ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â Character problem: One or more characters are missing, incorrect, or represented by unexpected invisible characters.

    These are different problems, so we need to identify which one we're dealing with before fixing anything.

    Case 1) : Word found normally
        For this we are not applying normalize text function and then we check.
        The results are, that some words are present normally and some can only be found when whitespace is ignored.

    Case 2) : We apply normalization and then checking
        For this we are going to apply normalize text function and then we check.
        The results are more worse then not normalize function, that some words are present normally and some can only be found when whitespace is ignored.





So, one thing is for sure we cannot just create a dictionary of words and replace the wrong words it is just hard coding and as pdf increases dictionary becomes too long and it becomes worse, so we are going to use one method:
    Step 1: Create a safe copy of the extracted text
        -- This one stays as original backup. We won't clean or modify this file. Whenever we want to test a cleaning method, we'll read this file and save the result somewhere else.

    Step 2: Save images of the PDF pages
        -- Suppose Python extracts ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ incorrectly. We need to look at the original PDF image to find out what the word actually says. The PDF image is our reference for checking the extracted text.

    Step 3: Check the text and clean
        1 - UTF-8 everywhere
            Setup
                Make sure Python reads and saves Hindi text using the correct encoding.
                For example, ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ should remain readable Hindi text rather than becoming garbage characters. We'll use encoding="utf-8" and ensure_ascii=False for JSON.



        2 - NFC normalization
            Basic cleaning
                Standardize Unicode representations so equivalent text is represented consistently.
                This does not repair every incorrectly extracted Hindi character.



        3 - Invisible characters
            Basic cleaning
                Look for hidden characters that could interfere with searching. Remove or replace them only after checking which ones occur and whether the change is safe.

        4 - Spaces and tabs
            Basic cleaning
                Remove unnecessary repeated spaces and tabs, but preserve line breaks. We'll need those line breaks for Step 6.



        5 - Punctuation
            Check before changing
                Check whether the Hindi sentence-ending mark ÃƒÂ Ã‚Â¥Ã‚Â¤ has been extracted correctly. If a | appears, inspect the original PDF before deciding whether it should be replaced.



        6 - Line-break repair
            Needs judgment
                Decide whether a line break should become a space or whether two text fragments belong together. We'll use conservative rules and verify uncertain cases against the page images.



        7 - Headers, footers and headings
            Check before removing
                Find repeated page text that shouldn't be included in the main content. Preserve section headings as metadata rather than throwing them away.



        8 - Mojibake check
            Validation
                Search for suspicious sequences such as ÃƒÆ’Ã‚Â Ãƒâ€šÃ‚Â¤ and ÃƒÆ’Ã†â€™, which can indicate an encoding problem. Report them for investigation rather than automatically replacing them.

    Step 4: Test whether our changes worked
        For each word, we'll check whether:
            - The word exists exactly as expected.
            - It appears only after ignoring whitespace.
            - It remains missing and needs investigation.
        If a word remains missing, we'll stop and inspect the extracted characters against the original PDF. We won't assume that normalization fixed everything.

        Instead of applying all functions at once we are going through use one by one and check which combinations are going through solve our problems.






    Conclusions for each combination:
        a) Just checking extracted pages directly without applying any function:
                Important terms such as ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â£ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬, SLV-III, ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â£-II, ÃƒÂ Ã‚Â¤Ã‚Â¡ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã¢â‚¬Â ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¡ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã¢â‚¬Å“, ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â£ ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬, and 27 ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‹â€  2015 were found in the expected extracted pages.

                Four terms require inspection because they were found only after whitespace was ignored: ÃƒÂ Ã‚Â¤Ã¢â‚¬ËœÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¨ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿, ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡, ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤, and ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â®.

                Eight terms were not found: ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¸ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã…Â¸ ÃƒÂ Ã‚Â¤Ã¢â‚¬ËœÃƒÂ Ã‚Â¤Ã‚Â« ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã¢â€šÂ¬, 15 ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â° 1931, ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Â¨, ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸, ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‹Å“ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¯, ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨, ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â°, and ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Âª.

                Pattern we have observed is, PyMuPDF is preserving some visual line breaks even when they occur inside Hindi words.

                Page	Raw extracted text	What the PDF shows
                4	        ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â¤	            ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤
                4	        ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â®	        ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â®
                8	        ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡	      ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡
                10	        ÃƒÂ Ã‚Â¤Ã¢â‚¬ËœÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¨\nÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿	   ÃƒÂ Ã‚Â¤Ã¢â‚¬ËœÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¨ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿

        b) Applying NFC Normalization only :
                NFC normalization made no changes to these pages. No differences were reported between the original and normalized text.


        c) Checking for invisible characters :
                The scanner did not find any characters matching its detection pattern in the 13 selected pages.
                It did not find the targeted zero-width characters, soft hyphens, BOM, non-breaking spaces, or other characters covered by that pattern.
                No characters were removed or modified by this inspection function.


        d) Checking Whitespace and Line Structure
                A separate inspect_whitespace() function was implemented in check_PyMuPDF_Words.py to inspect whitespace patterns in the extracted text across the 13 selected pages.

                The function checks:
                    Leading whitespace at the beginning of lines.
                    Trailing whitespace at the end of lines.
                    Repeated ordinary spaces.
                    Tab characters.
                    Empty lines.
                    Line-break counts for each page.

                Results:
                    25 line-level issues were reported, all related to leading whitespace.
                    No trailing whitespace, repeated-space, or tab warnings were reported in the displayed output.
                    Zero empty lines were reported on the inspected pages.
                    Line-break counts were printed for each page.

                Leading whitespace may result from PDF layout or indentation and is not automatically an extraction error. Similarly, line breaks can represent legitimate sentence, paragraph, or layout boundaries. Therefore, no whitespace was removed or normalized during this inspection.


        e) Checking Word-Level Structure
                A separate inspect_word_structure() function was added to identify possible word splits across line breaks in the extracted text.

                The function searches for Devanagari text on both sides of a newline and reports the page number, character position, and matching text. This helps identify candidates for manual inspection.

                Examples identified:
                    Page 4: ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â¤
                    Page 4: ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â®
                    Page 8: ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡
                    Page 10: ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿
                    Page 13: ÃƒÂ Ã‚Â¤Ã¢â‚¬Â°ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿
                    Page 15: ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿\nÃƒÂ Ã‚Â¤Ã‚Â°

                Previously inspected examples confirmed that some words were split across line breaks in the raw extraction.

                The current pattern also reports ordinary line breaks between separate words, such as ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¨\nÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â® and ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã…Â¡ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¡\nÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã‚Â§ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢. Therefore, its output is a list of possible issues, not a list of confirmed word-splitting errors.

                Each candidate must be evaluated using its surrounding text and, where necessary, the original PDF page image.





So, all gave no significant help so at last we are going through two rules: Rule A and Rule B




# Hindi PDF Extraction and RAG Preparation --- Rule A & Rule B

## 1. Project overview

**Project folder:** `C:\Agents\RAG`\
**Source PDF:** `data\Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf`

The goal of this stage is to prepare extracted Hindi text for a
Retrieval-Augmented Generation (RAG) pipeline. We are correcting
selected extraction issues while preserving the original extraction and
recording changes.

Our approach is deliberately conservative: - No Hindi dictionary or
dictionary expansion. - No LLM-based correction in Rule B. - No
page-specific word-correction rules. - No attempt to fix every cosmetic
formatting issue. - Prioritize names, dates, identifiers, and technical
terms. - Keep raw text, processed text, experiments, and validated
backups separate.

> Successful script execution and keyword presence do not prove that
> every extracted word is correct.

## 2. Input data and page scope

The workflow currently uses 13 selected PDF pages. The original
extraction is stored in:

``` text
verification/raw_pages/pymupdf_raw.json
```

Treat this file as the immutable baseline. Cleaning stages write
separate outputs and should not overwrite the raw extraction.

------------------------------------------------------------------------

# 3. Rule A --- Duplicate vowel-sign cleaning

## 3.1 Why Rule A was needed

The initial PyMuPDF extraction contained examples of adjacent repeated
Devanagari vowel signs:

  Extracted form   Intended form
  ---------------- ---------------
  `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â°`          `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â°`
  `ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Âª`          `ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Âª`
  `ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢`       `ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢`
  `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â²`            `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â²`
  `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â£`         `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â£`
  `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¤`          `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¤`

We inspected Unicode code points and confirmed that examples such as
`ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â°` contained two adjacent copies of the same vowel-sign character.
This supported a general character-level rule instead of a list of
word-specific replacements.

## 3.2 What Rule A does

Rule A checks for two identical eligible Devanagari vowel signs
immediately next to each other and keeps one copy. It applies the same
pattern-based rule wherever it occurs.

Rule A does **not**: - repair words split across line breaks; - insert
spaces missing between separate words; - correct arbitrary missing or
misrecognized characters; - reconstruct tables or reading order; - prove
that every duplicate it removes was erroneous.

## 3.3 Rule A files

  ----------------------------------------------------------------------------------
  File                                           Purpose
  ---------------------------------------------- -----------------------------------
  `check_PyMuPDF_Words.py`                       Diagnostic checks for extracted
                                                 words and Unicode characters.

  `rule_a_vowel_sign_cleaner.py`                 Applies the Rule A cleaning
                                                 operation.

  `verification/raw_pages/pymupdf_raw.json`      Original extraction; preserve
                                                 unchanged.

  `data/processed/pymupdf_rule_a_cleaned.json`   Text produced by Rule A.

  `data/processed/rule_a_audit.json`             Audit records for Rule A changes.
  ----------------------------------------------------------------------------------

## 3.4 What Rule A achieved

The targeted scan reported **93 adjacent duplicate vowel-sign
occurrences** across the selected pages. The earlier Rule A run reported
93 changes:

  Code point      Count
  ------------ --------
  U+093E             57
  U+0940             14
  U+0941              2
  U+0942              6
  U+0947             10
  U+094B              4
  **Total**      **93**

Eight selected test words were found in the cleaned text: `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¤Ã‚Â°`,
`ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Âª`, `ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨`, `ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‹â€ ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã…Â¾ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢`, `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â²`, `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â£`, `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¤`, and `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â²`.

These results show that the rule ran and the selected test words were
present. They do **not** establish that every one of the 93 changes was
correct; not every occurrence has been individually compared with the
PDF image.

------------------------------------------------------------------------

# 4. Rule B --- Generic line-boundary reconstruction

## 4.1 Why Rule B was needed

Rule A only handles adjacent repeated vowel signs. The extracted text
also contains line breaks inside words or phrases, for example:

``` text
ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â·ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿
ÃƒÂ Ã‚Â¤Ã‚Â¯ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¾
```

The original PDF shows `ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â·ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¾`.

Deleting every newline would be unsafe because some line breaks
represent paragraph boundaries, headings, list items, or sentence
boundaries. Rule B therefore classifies each boundary and chooses how to
join the lines.

## 4.2 What Rule B does

Rule B reads the Rule A output and proposes one of these decisions for
each line boundary:

-   `KEEP_NEWLINE` --- retain the newline.
-   `JOIN_WITH_SPACE` --- join the lines with a space.
-   `JOIN_NO_SPACE` --- join without a space, mainly for a
    punctuation-only continuation.
-   `REVIEW` --- mark a boundary for manual review.

The current generic classifier checks empty lines, bullets/list
boundaries, punctuation-only lines, sentence-ending punctuation, and
numbered section headings. Otherwise, it uses a conservative
space-joining default.

This is a heuristic. It cannot reliably infer every split Hindi word,
and some boundaries may still be joined or preserved incorrectly. We
decided not to keep adding rules just to fix every formatting issue.

## 4.3 Rule B files

  -------------------------------------------------------------------------------------------
  File                                                    Purpose
  ------------------------------------------------------- -----------------------------------
  `build_rule_b.py`                                       Builds boundary decisions and
                                                          applies them to the Rule A output.

  `data/processed/rule_b_manual_review_experiment.csv`    Boundary review CSV with proposed
                                                          decisions and an optional
                                                          `final_decision` field.

  `data/processed/clean_pages_B_experiment.json`          Experimental reconstructed text
                                                          produced by Rule B.

  `data/processed/audit_rule_b_experiment.csv`            Audit log of boundary decisions and
                                                          separators used.

  `build_rule_b_validated_backup.py`                      Preserved backup script from an
                                                          earlier version.

  `data/processed/clean_pages_AB_validated_backup.json`   Preserved earlier output.

  `data/processed/audit_rule_b_validated_backup.csv`      Preserved earlier audit output.
  -------------------------------------------------------------------------------------------

**Keep the experimental output separate from the validated backup.**

## 4.4 Current Rule B run and result

The latest build produced:

``` text
Input pages: 13
Boundaries reviewed: 208
Proposed decisions:
  KEEP_NEWLINE: 65
  JOIN_WITH_SPACE: 143
```

The subsequent `apply` run completed:

``` text
Pages processed: 13
Boundaries applied: 208
Decision sources: {'proposed': 208}
Output: data/processed/clean_pages_B_experiment.json
Audit: data/processed/audit_rule_b_experiment.csv
```

This confirms that the script processed all 208 boundaries and wrote the
experimental output and audit CSV. It does not prove that all 208
decisions are semantically correct.

## 4.5 What we checked after Rule B

We searched the reconstructed text for important dates, names, and
identifiers. The checks found:

-   Years: `1931`, `2015`, `1979`, `1980`, `1998`, `2002`, `2007`
-   Technical identifier: `SLV-III`
-   Organization names in Hindi: `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹`, `ÃƒÂ Ã‚Â¤Ã‚Â¡ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã¢â‚¬Â ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¡ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã¢â‚¬Å“`
-   Names: `ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â® ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â­ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‹â€ `, `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚Â¶ ÃƒÂ Ã‚Â¤Ã‚Â§ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¨`, `ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¦ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â£ ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬`

The first check did not find English `Rohini`. Inspecting page 8 showed
`ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â£ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬`, the Hindi spelling of the satellite name, alongside the July
1980 successful launch description. The English-only check was therefore
a false alarm.

We also compared selected phrases from page 11 with the original PDF
screenshot. The source showed `ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â·ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¾`, `ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¾ ÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â`,
and `ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬â€ÃƒÂ Ã‚Â¤Ã‚Â¤ ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¸`.

Some minor issues remain, including broken words and missing spaces. We
decided not to add dictionary-based, LLM-based, or page-specific
correction rules for these issues. We can tolerate minor formatting
defects where they do not materially affect meaning, while prioritizing
critical facts and identifiers.

------------------------------------------------------------------------

# 5. Rule A + Rule B combined: what we achieved

The pipeline so far is:

``` text
Original PDF
    |
    v
PyMuPDF raw extraction
    |
    v
verification/raw_pages/pymupdf_raw.json
    |
    v
Rule A: remove adjacent duplicate eligible vowel signs
    |
    +--> data/processed/pymupdf_rule_a_cleaned.json
    +--> data/processed/rule_a_audit.json
    |
    v
Rule B: classify and reconstruct line boundaries
    |
    +--> data/processed/clean_pages_B_experiment.json
    +--> data/processed/audit_rule_b_experiment.csv
```

Together, Rule A and Rule B have: 1. Preserved the raw extraction as a
separate baseline. 2. Applied a general character-level cleaning rule
for adjacent duplicate vowel signs. 3. Reconstructed line boundaries
using generic structural heuristics. 4. Generated audit records for
changes and boundary decisions. 5. Produced an experimental
reconstructed text for the 13 selected pages. 6. Checked selected names,
dates, and technical identifiers. 7. Confirmed the Hindi spelling
`ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã‚Â¹ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â£ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬` and the July 1980 launch description on page 8.










Table Extraction, Cleaning, and Document Combination
Overview
This stage prepares the tables and the prose around them from the Hindi
PDF for RAG. It keeps the original extracted data unchanged and saves
cleaned outputs separately.
1. Extract the tables
Script: inspect_tables.py
The script extracts tables from PDF pages 9, 12, 16, 17, 20, and 22
using PyMuPDF's table detection.
It saves the raw table extraction to:
- verification/raw_tables/tables_raw_clip.json
It also extracts prose outside the table areas on those same pages and
preserves it in:
- verification/raw_pages/pymupdf_raw_tablepages.json
Existing raw files are preserved rather than overwritten.
2. Clean the tables
The same inspect_tables.py script cleans the extracted table cells and
records an audit.
Main outputs:
- data/processed/tables_clean.json --- cleaned tables, including
  section title, page, row/column counts, and cells.
- data/processed/tables_clean_audit.csv --- log of table-cleaning
  changes and checks.
- data/processed/table_cell_breaks_review.csv --- cell line-break
  review.
- data/processed/table_rows.json and tables_display.json ---
  additional table representations.
Rule A is applied to table cells to collapse adjacent repeated identical
Devanagari vowel signs. This is a limited mechanical rule; it does not
correct arbitrary Hindi spelling or OCR mistakes.
The six cleaned tables contain 55 rows in total, including headers,
across the six pages.
3. Clean prose from pages that contain tables
Those six pages contain both tables and ordinary prose. The prose
outside table areas is handled separately from the tables.
Rule A
Script: prepare_tablepage_prose.py
Input:
- verification/raw_pages/pymupdf_raw_tablepages.json
Rule A applies Unicode-preserving text cleanup and collapses adjacent
repeated identical Devanagari dependent vowel signs.
Outputs:
- data/processed/pymupdf_rule_a_tablepages.json
- data/processed/rule_a_tablepages_audit.json
In the current run, Rule A made 19 changes across the six prose records.
Rule B
Rule B handles physical line boundaries in extracted prose. It joins
lines using boundary decisions and records those decisions in an audit.
It does not use a dictionary or an LLM.
For the six mixed-page prose records, the pipeline writes:
- data/processed/clean_tablepage_prose_AB.json --- Rule A+B prose
  output.
- data/processed/rule_b_tablepages_manual_review.csv --- separate
  boundary-review file.
- data/processed/audit_rule_b_tablepages.csv --- Rule B audit.
The latest run processed 18 boundaries, all defaulted to
JOIN_WITH_SPACE. These are processing decisions, not proof that
every boundary is correct; review the CSV when validating text
quality.
The existing validated prose from the other 13 pages remains in
data/processed/clean_pages_AB.json and is not overwritten by this
mixed-page processing.
4. Combine prose and tables
Main pipeline: process_document.py
The pipeline reuses the existing validated 13-page prose, the cleaned
prose from the six mixed pages, and the six cleaned tables. It combines
them into:
- data/processed/final_document.json
The combined JSON has 25 records:
- 19 prose records from pages 3--20 and 22 (page 21 is not part of
  this extracted set).
- 6 table records from pages 9, 12, 16, 17, 20, and 22.
Each prose record keeps its page number, section number/title, text, and
type. Each table record keeps its page, section metadata, dimensions,
and cell grid.
5. Validation performed
The combined document was checked and passed these structural checks:
- 25 records total: 19 prose and 6 tables.
- Expected 19 prose pages are present exactly once.
- All six expected table pages are present.
- Every record contains prose text or table content.
- Table section titles and row counts were inspected.
Table row counts, including header rows:
PDF page Section                      Rows
       9 ÃƒÂ Ã‚Â¤Ã‚Â¨ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤ ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â² ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¯ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â®          6
      12 ÃƒÂ Ã‚Â¤Ã¢â‚¬â€ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã‚Â ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â·ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢                     6
      16 ÃƒÂ Ã‚Â¤Ã‚ÂªÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â° ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â¨                 6
      17 ÃƒÂ Ã‚Â¤Ã…â€œÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â¨-ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã¢â‚¬â€œÃƒÂ Ã‚Â¤Ã‚Â¾ (ÃƒÂ Ã‚Â¤Ã…Â¸ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â®ÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¡ÃƒÂ Ã‚Â¤Ã‚Â¨)            14
      20 ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Å“ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¥Ã¢â‚¬Â¹ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ ÃƒÂ Ã‚Â¤Ã¢â‚¬Â¢ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬ ÃƒÂ Ã‚Â¤Ã‚Â¶ÃƒÂ Ã‚Â¤Ã‚Â¬ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¦ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â²ÃƒÂ Ã‚Â¥Ã¢â€šÂ¬       10
      22 ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚ÂµÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¿ÃƒÂ Ã‚Â¤Ã‚Â¤ ÃƒÂ Ã‚Â¤Ã‚Â¤ÃƒÂ Ã‚Â¤Ã‚Â¥ÃƒÂ Ã‚Â¥Ã‚ÂÃƒÂ Ã‚Â¤Ã‚Â¯-ÃƒÂ Ã‚Â¤Ã‚Â¸ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã‚Â°ÃƒÂ Ã‚Â¤Ã‚Â¾ÃƒÂ Ã‚Â¤Ã¢â‚¬Å¡ÃƒÂ Ã‚Â¤Ã‚Â¶                13
6. Run and output notes
Run commands from the project root, C:\Agents\RAG:
python .\inspect_tables.py
python .\prepare_tablepage_prose.py
python .\process_document.py
Only rerun a stage after checking whether its output already exists;
some scripts deliberately preserve raw files or refuse to overwrite
existing outputs.
Important limitations
- Structural validation confirms record/page coverage, not perfect
  Hindi OCR or spelling accuracy.
- Rule A only handles adjacent duplicate vowel signs.
- Rule B line joins still require content-level review.
- The original raw extraction files are the reference for
  investigating suspected errors.
- No dictionary-based correction or LLM correction is used in this
  stage.
Current stopping point: extraction, cleaning, table handling,
combination, and structural validation are complete. Chunking,
embeddings, vector indexing, and retrieval evaluation are separate next
stages.






# Chunking

The chunking stage reads `data/processed/final_document.json`, which contains validated prose and structured tables.

Two chunking strategies are used:

- **Prose chunking:** Splits text at meaningful paragraph and sentence boundaries, with a fallback for unusually long sentences.
- **Table chunking:** Preserves table headers and groups data rows so each chunk retains its column context.

Each chunk stores metadata such as:

- `chunk_id`: Stable ID generated using a SHA-256 hash.
- `content`: The text used for retrieval.
- `source_page`: Original PDF page number.
- `content_type`: `prose` or `table`.
- `chunk_index`: Chunk number within its source record.
- Additional section or table metadata when available.

Chunk sizes are starting parameters, not assumed optimal values. They can be evaluated and adjusted during retrieval testing.

**Current validation results:**
- Source records: 26 (20 prose and 6 tables).
- Total chunks: 32 (21 prose and 11 table chunks).
- Empty chunks: 0.
- Duplicate chunk IDs: 0.
- Missing source pages: 0.
- Table data rows represented in chunk metadata: 49 of 49.
- All 6 source table pages are covered.

These checks confirm structural coverage; retrieval quality and exact text preservation require separate evaluation.

**Next stages:** embeddings, vector indexing, retrieval evaluation, and answer generation with source citations.