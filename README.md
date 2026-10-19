# Hindi Document RAG: A. P. J. Abdul Kalam — *Agni Ki Udaan*

## Project Overview

This project implements a Retrieval-Augmented Generation (RAG) system that answers questions about the Hindi document *Agni Ki Udaan* using information retrieved from the document itself.

The system accepts questions in Hindi or English, retrieves relevant passages from the Hindi document, sends those passages to Gemini, and returns an answer with source metadata such as the PDF page number, section title, chunk ID, and retrieval similarity score.

The main challenge was not simply connecting an LLM to a vector database. The original document contains Hindi text, technical terms, tables, and PDF layout artifacts. Incorrectly extracted text can lead to poor retrieval, so the project includes a document-preparation workflow before the RAG pipeline.

### Main technologies

| Component | Technology | Purpose |
|---|---|---|
| PDF extraction | PyMuPDF | Extract text and inspect PDF tables |
| Text cleaning | Python, Unicode normalization, Rule A and Rule B | Prepare readable Hindi text |
| Document storage | JSON | Preserve processed text, metadata, and chunks |
| Embeddings | `BAAI/bge-m3` | Represent Hindi text and English questions as vectors |
| Vector database | ChromaDB | Store vectors, text, and source metadata |
| Answer generation | Google Gemini API | Generate answers from retrieved evidence |
| Evaluation | Custom Python evaluation in `rag.py` | Measure retrieval performance on six benchmark questions |

---

## 1. Understanding the Complete Pipeline

The project has two major parts: document preparation and question answering.

```text
ORIGINAL HINDI PDF
        |
        v
1. Extract PDF text and inspect tables
        |
        v
2. Rule A: clean selected duplicate vowel signs
        |
        v
3. Rule B: classify and reconstruct line boundaries
        |
        v
4. Extract and clean tables separately
        |
        v
5. Combine cleaned prose and tables
        |
        v
6. Create semantic chunks with metadata
        |
        v
7. Generate BGE-M3 embeddings
        |
        v
8. Store vectors and metadata in ChromaDB
        |
        v
       INDEX READY
        |
        v
USER ASKS A QUESTION IN HINDI OR ENGLISH
        |
        v
9. Embed the question and retrieve relevant chunks
        |
        v
10. Send retrieved evidence to Gemini
        |
        v
11. Generate an evidence-grounded answer
        |
        v
12. Attach citations using retrieved metadata
```

Each stage has a different responsibility. Cleaning improves the text, chunking organizes it, embeddings represent its meaning numerically, ChromaDB retrieves relevant passages, and Gemini generates the final answer.

## 2. PDF Extraction and Text Preparation

### 2.1 Why PDF extraction needed attention

A PDF is primarily a document-layout format. Extracting its text does not always reproduce the original reading order or word boundaries perfectly.

This matters especially for Hindi because Devanagari uses dependent vowel signs, conjuncts, and other Unicode characters. An extraction error can cause a word to become incomplete or unreadable.

For example, a word may be visually correct in the original PDF but contain an unwanted line break in the extracted text. A different problem occurs when a character is duplicated or missing. These two problems require different treatments.

The project initially compared PyMuPDF, pdfplumber, and pypdf on selected pages. The outputs differed, and null characters and damaged text patterns were observed in some outputs. PyMuPDF was selected as the preferred extraction method for further inspection, but its output was not assumed to be perfect.

The workflow therefore used separate raw, processed, and audit files rather than treating the first extraction as final.

### 2.2 Unicode normalization

Unicode allows some visually equivalent text to be represented in different ways. NFC normalization converts eligible equivalent sequences into a consistent representation.

Python example:

```python
import unicodedata

text = unicodedata.normalize("NFC", text)
```

This helps make text comparisons and searching more consistent.

However, Unicode normalization does not restore a missing character, repair every Hindi spelling, or automatically fix words split across lines. Those problems need separate investigation.

The project also uses UTF-8 when working with text files and JSON so Hindi characters can be preserved correctly.

### 2.3 Rule A: Duplicate vowel-sign cleaning

**Purpose:** Rule A targets adjacent duplicate copies of selected Devanagari dependent vowel signs.

During inspection, the extracted text contained examples where the same eligible vowel sign appeared twice consecutively. This can introduce an extra character into a word and affect both readability and retrieval.

Rule A applies a general character-level pattern rather than maintaining a list of individual words to replace.

Conceptually:

```text
Input:  consonant + vowel sign + same vowel sign
                    |
                    v
Rule A: keep one copy of the adjacent duplicate
                    |
                    v
Output: consonant + vowel sign
```

The actual implementation checks eligible Devanagari vowel-sign characters and collapses adjacent identical copies.

The earlier Rule A run reported 93 changes across the selected pages. This confirms that the rule found and changed matching patterns; it does not prove that every change was correct. Each change would need source-PDF verification to establish that.

**What Rule A does not do:**

- Reconstruct words split across lines.
- Insert missing spaces between separate words.
- Correct arbitrary spelling or character-recognition errors.
- Fix all table-layout problems.
- Guarantee that every cleaned sentence is accurate.

The purpose of Rule A is deliberately narrow: correct a repeated-character pattern without using a Hindi dictionary, a word-specific replacement list, or an LLM to rewrite the document.

Audit files record changes so that the cleaning process can be investigated instead of being treated as a black box.

### 2.4 Rule B: Generic line-boundary reconstruction

**Purpose:** Rule B handles line boundaries that may split words or phrases during PDF extraction.

PDF extraction can preserve visual line breaks even when a word continues on the next line. At the same time, a newline can represent a real paragraph boundary, a heading, a list item, or the end of a sentence.

Deleting every newline would therefore be unsafe.

Rule B classifies line boundaries into four decision types:

- `KEEP_NEWLINE`: preserve the line break.
- `JOIN_WITH_SPACE`: join the lines with a space.
- `JOIN_NO_SPACE`: join without a space for the limited cases where that is appropriate.
- `REVIEW`: flag the boundary for manual inspection.

The current classifier uses structural clues such as empty lines, list markers, punctuation, sentence endings, and numbered headings. Other boundaries use a conservative joining heuristic.

For example, if a word is split between two physical lines, joining the fragments may restore the word. If the newline separates two sentences or a heading and its content, retaining the boundary may be more appropriate.

These decisions are heuristic rather than linguistically perfect. A generic rule cannot infer every Hindi word boundary correctly.

The workflow writes reconstructed text and audit information separately. The audit makes it possible to inspect which decisions were made and which cases deserve further review.

**What Rule B does not guarantee:** It does not prove that every line has been joined correctly, recover arbitrary missing characters, or fully understand Hindi grammar. It reduces certain layout problems while preserving a record of the transformations.

### 2.5 Table extraction and cleaning

Ordinary prose extraction is not sufficient for a document that contains tables. A table may include dates, awards, timelines, technical identifiers, and short factual descriptions. Flattening it into a single paragraph can lose the relationships between rows and columns.

The project therefore handles tables separately from the prose surrounding them.

The table-processing workflow uses PyMuPDF table detection and includes the table pages 9, 12, 16, 17, 20, and 22. The extracted tables are cleaned, reviewed, and represented in structured JSON files. Prose outside the table areas is processed separately so that table text and surrounding paragraphs are not unnecessarily mixed together.

The current table-processing notes record six cleaned tables with 55 rows in total, including headers.

Rule A is also applied to table cells for the limited duplicate-vowel-sign pattern. Table cleaning does not mean that every cell has been proven accurate; suspicious rows and line breaks still require comparison with the original PDF.

The final document preparation stage combines the processed prose and table content so both kinds of evidence can be used during retrieval.

### 2.6 Why the cleaning workflow is conservative

The project deliberately avoids:

- A manually maintained Hindi dictionary for replacing words.
- Broad replacements based on guesses about damaged text.
- Automatic LLM rewriting of the source document.
- Assuming that a script running successfully means the output is correct.

The original PDF is the reference for verification. When a suspicious character or word cannot be confidently resolved from the extracted text, it should be inspected against the page image rather than guessed.

This approach is important because a visually plausible correction can still change a name, date, technical identifier, or factual statement.

---

## 3. Semantic Chunking

### 3.1 What is a chunk?

An embedding model and a vector database work with individual pieces of text called chunks. Instead of retrieving an entire book for every question, the system retrieves a smaller passage that is likely to contain the answer.

For example, a question about the year of the SLV-III launch should retrieve the passage or table row describing that launch, rather than the entire biography.

A chunk contains text and source metadata. The metadata lets the application trace a retrieved passage back to its original location.

### 3.2 Why semantic chunking was chosen

Fixed-size chunking splits text after a predetermined number of characters or tokens. It is straightforward, but it can split a sentence or separate a heading from the information it describes.

Semantic chunking attempts to place boundaries where the content changes meaning or topic. This is useful for a biography containing sections about Kalam's education, scientific career, awards, presidency, and final years.

The project uses a semantic chunking process that considers neighboring text similarity, structural boundaries, sentence-ending punctuation, and chunk-length limits.

The current configuration includes these important settings:

| Setting | Value | Meaning |
|---|---:|---|
| Minimum chunk threshold | About 250 characters | Usually avoids splitting a topic too early |
| Maximum chunk target | About 1,100 characters | Encourages chunks to remain manageable |
| Heading threshold | About 120 characters | Allows a new heading to start a new chunk once the previous chunk is sufficiently developed |
| Semantic split percentile | 25th percentile | Uses relatively low neighboring similarity as a signal for a topic boundary |
| Retrieval `TOP_K` | 5 | Retrieves up to five relevant chunks for a query |

These are character-based configuration values, not token counts. The actual chunk lengths can vary because the algorithm also considers semantic and structural boundaries.

### 3.3 How the semantic splitting decision works

At a high level, the chunking process follows these steps:

1. Read the prepared document and preserve its source information.
2. Identify structural units such as sections, paragraphs, and table rows.
3. Split long text at suitable Hindi sentence boundaries, including the danda (`।`), while avoiding unsafe splits at ordinary periods in abbreviations.
4. Compare neighboring text units using semantic similarity.
5. Consider a split when neighboring units appear less related, subject to minimum and maximum length rules.
6. Keep table rows as separate retrievable units so that individual facts remain accessible.
7. Store the resulting chunks with their page, section, and chunk ID metadata.

The semantic split percentile is a decision signal, not a guarantee that every resulting chunk contains exactly one topic. The minimum and maximum length rules help balance context against retrieval precision.

### 3.4 Why table rows are separate chunks

Consider a timeline table containing an event and its year. If many rows are combined into a single large chunk, a question about one event may retrieve unrelated events too.

Keeping rows separate helps the retriever locate the relevant date or fact and preserves a clear citation target. Table-row chunks are particularly useful for questions about awards, dates, and technical milestones.

### 3.5 Does the project use overlap?

The current chunking design does not use a fixed-size sliding window with a configured overlap. It builds chunks around semantic and structural boundaries instead.

This avoids automatically repeating a fixed amount of text in every adjacent chunk. A possible future improvement would be to test limited overlap where important context is split across a boundary and compare its effect on retrieval quality.

### 3.6 Chunk metadata

Each chunk keeps metadata that can include:

- `chunk_id`: a unique identifier for the chunk.
- `page`: the source PDF page number.
- `section_title`: the associated section heading.
- `content`: the text used for retrieval and generation.

These fields are important because retrieval quality alone is not sufficient. The application must also be able to explain where the evidence came from.

---

## 4. Embeddings and ChromaDB

### 4.1 What is an embedding?

An embedding is a numerical vector representing text. Texts with related meanings can have similar vector representations, which allows semantic retrieval even when the question and source passage do not use exactly the same words.

For example, an English question about an aeronautical engineering institution can retrieve a Hindi passage about Kalam's education if their embeddings represent the relevant meaning similarly.

This is especially useful for cross-lingual retrieval: the question can be in English while the evidence is in Hindi.

### 4.2 Why BGE-M3?

The project uses `BAAI/bge-m3`, a multilingual embedding model suitable for representing text from multiple languages.

The model converts each document chunk into a vector. During a query, the question is also embedded so the system can compare it with the stored chunk vectors.

The model is used for semantic retrieval; it does not generate the final answer. Gemini performs answer generation later.

### 4.3 Why ChromaDB?

ChromaDB is an open-source vector database that runs locally and supports persistent storage.

The project uses it to store the chunk vectors, their text, and their metadata. Once the index has been created, the application can reopen the local collection and search it without embedding the entire document again for every question.

The configured collection is `kalam_hindi_semantic`, and the local database directory is `data/processed/chroma_db_semantic`.

The vector database is a generated artifact. It is excluded from Git because it can be rebuilt from the prepared chunks and does not need to be committed alongside the source code.

### 4.4 What happens during indexing?

Indexing prepares the document for retrieval:

1. Load the prepared semantic chunks.
2. Generate an embedding for each chunk using BGE-M3.
3. Store the vectors in ChromaDB.
4. Store the corresponding chunk text and metadata.
5. Make the collection available for future searches.

Indexing is a separate operation from answering questions. This separation avoids repeatedly rebuilding the vector database whenever a user asks something.

---

## 5. Retrieval and Answer Generation

### 5.1 Step 1: Receive a question

The user can ask a question in Hindi or English.

Examples:

- `SLV-III ने किस उपग्रह को कक्षा में स्थापित किया और किस वर्ष?`
- `Which institution did Kalam attend to study aeronautical engineering?`

### 5.2 Step 2: Retrieve relevant chunks

The question is converted into an embedding and compared with the vectors stored in ChromaDB.

The application retrieves up to five relevant chunks by default. Each result includes its source metadata and a similarity score.

The score indicates how closely the embedding-based retrieval method considers the question and passage to be related. It is not a probability that the passage is factually correct.

### 5.3 Step 3: Build the evidence context

The retrieved passages are assembled into a context for Gemini. Each passage is labelled with information such as its chunk ID, page, section title, and similarity score.

This helps the model distinguish the retrieved evidence and follow the source content rather than relying only on general knowledge.

### 5.4 Step 4: Generate the answer with Gemini

The project uses the Google Gemini API, configured through environment variables:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`

The prompt instructs the model to use only the supplied evidence, avoid guessing, and indicate when the evidence is insufficient or contradictory.

The generation temperature is set to zero to reduce randomness. This does not guarantee factual correctness, so answers still need to be evaluated against their supporting passages.

### 5.5 Step 5: Attach citations

The application attaches citation metadata using the actual retrieved results. It does not depend on the model inventing page numbers or chunk IDs.

A source record can contain:

- PDF page number.
- Section title.
- Chunk ID.
- Similarity score.

This provides traceability: a reviewer can locate the source passage and compare it with the generated answer.

The retrieved passages and their citations are evidence candidates, not automatic proof that every statement in the answer is supported. For high accuracy, the answer must be checked against the retrieved text and, when necessary, the original PDF.

---

## 6. Evaluation

The project includes six benchmark questions covering a technical milestone, an award, a scientific role, education, autobiography publication, and Kalam's death.

The retrieval evaluation checks whether the expected supporting chunk is present among the retrieved results. It reports Hit@1, Hit@3, Hit@5, and Mean Reciprocal Rank (MRR).

### Recorded retrieval results

| Metric | Result |
|---|---:|
| Hit@1 | 5/6 — 83.3% |
| Hit@3 | 6/6 — 100% |
| Hit@5 | 6/6 — 100% |
| MRR | 0.917 |

**How to interpret these results:**

- **Hit@1:** The expected evidence was ranked first for five of the six benchmark questions.
- **Hit@3:** The expected evidence appeared within the top three results for all six questions.
- **Hit@5:** The expected evidence appeared within the top five results for all six questions.
- **MRR:** This measures how highly the first relevant result is ranked, with higher values indicating better rankings.

These are the recorded results from the current retrieval evaluation. They do not prove that every generated answer is correct, that every citation is sufficient, or that the system will achieve the same scores on unseen questions.

The `results.md` file records the six generated answers and their retrieved source metadata. The benchmark should be rerun after changes to extraction, chunking, embeddings, or retrieval settings.

---

## 7. Limitations and Future Improvements

### Current limitations

1. **Extraction accuracy:** Generic extraction and cleaning rules can leave some Hindi text errors. Not every character or table cell has been individually verified against the original PDF.
2. **Rule A limitations:** Removing adjacent duplicate vowel signs is a narrow transformation. The number of changes alone does not prove that all changes were correct.
3. **Rule B limitations:** Line-boundary reconstruction is heuristic and may join or preserve some lines incorrectly.
4. **Semantic retrieval:** Embedding similarity can rank a related passage above the exact passage needed for a question.
5. **Generation:** Gemini can still omit a detail or make an unsupported inference despite receiving retrieved evidence.
6. **Evaluation scope:** Six benchmark questions provide a useful starting point but are too few to establish general accuracy.

### Improvements with more time

- Verify additional extracted Hindi text and table cells against the original PDF.
- Review uncertain Rule A and Rule B changes using the audit files.
- Expand the benchmark set and evaluate retrieval and answer correctness separately.
- Test hybrid retrieval that combines vector similarity with keyword matching.
- Test reranking to improve the order of retrieved passages.
- Add automated checks that compare answer claims with their cited evidence.
- Add tests for missing metadata, empty retrieval results, unsupported questions, and clean-environment installation.
- Compare chunking configurations using the same benchmark questions rather than choosing parameters based only on intuition.

---

## 8. Installation and Usage

### Prerequisites

- Python 3.11 recommended.
- Git.
- A Gemini API key for answer generation.
- Sufficient disk space for the embedding model and the local vector database.

Run commands from the project root.

### Step 1: Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv RAG
.\RAG\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### Step 2: Install dependencies

```powershell
pip install -r requirements.txt
```

The `requirements.txt` file should contain the pinned package versions used by the project.

### Step 3: Configure Gemini

Create a `.env` file in the project root:

```text
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Replace the placeholder with your own API key. Do not commit `.env` to Git. The repository should include `.env.example` containing variable names only, without a real secret.

### Step 4: Prepare semantic chunks

```powershell
python rag.py chunk
```

This command runs the chunking stage using the prepared document and writes the chunk data expected by the application.

### Step 5: Build the vector index

```powershell
python rag.py index
```

This generates embeddings with BGE-M3 and stores the vectors and associated metadata in the local ChromaDB collection.

The first run may download the embedding model and can take longer than later runs.

### Step 6: Ask an individual question

```powershell
python rag.py answer "कलाम को भारत रत्न किस वर्ष प्राप्त हुआ?"
```

The command retrieves relevant chunks, generates an answer with Gemini, and displays the retrieved source metadata.

### Step 7: Run the six-question benchmark

```powershell
python rag.py answers
```

This runs the required benchmark questions and generates the benchmark output. The submission file `results.md` should contain the actual generated answers and their citations. If the command writes to `answers.md`, copy the resulting output to `results.md` after the run.

### Step 8: Evaluate retrieval

```powershell
python rag.py eval
```

This reports the retrieval metrics for the six benchmark questions.

### Reproducibility notes

- Run commands from the project root.
- Keep the source PDF and required processed JSON files in their documented locations.
- Keep API keys in `.env`, not in source code or committed files.
- The local ChromaDB directory is generated by indexing and is not included in Git.
- Model downloads and API calls may require an internet connection.
- For a new environment, install dependencies and rebuild the index before asking questions.

---

## 9. Project Files

The main project files include:

| File or directory | Purpose |
|---|---|
| `rag.py` | Chunking, indexing, retrieval, Gemini generation, benchmark, and evaluation commands |
| `requirements.txt` | Python dependencies and pinned versions |
| `.env.example` | Template showing the required environment-variable names |
| `.gitignore` | Excludes secrets, virtual environments, local databases, and generated artifacts |
| `data/Agni_Ki_Udaan_Adhyayan_Sahayika_Hindi.pdf` | Original source PDF |
| `data/processed/final_document.json` | Prepared document content used by the pipeline |
| `data/processed/chunks.json` | Chunk representation from the document-preparation workflow |
| `data/processed/semantic_chunks.json` | Semantic chunks used by the current RAG configuration |
| `data/processed/chroma_db_semantic/` | Local generated ChromaDB index; rebuild with the indexing command |
| `results.md` | Six benchmark questions, generated answers, and retrieved source metadata |

Additional extraction scripts, table-processing files, and audit outputs document how the source text was prepared.

## Conclusion

This project demonstrates an end-to-end RAG workflow for a Hindi document: conservative text preparation, semantic chunking, multilingual embeddings, persistent vector search, LLM-based answer generation, source metadata, and retrieval evaluation.

The central design principle is that answer quality depends on the entire pipeline. Better generation alone cannot compensate for damaged source text, poor chunk boundaries, irrelevant retrieval, or missing citations. The project therefore treats document preparation, retrieval, generation, and evaluation as separate stages that can be inspected and improved independently.
