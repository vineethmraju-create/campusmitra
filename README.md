# CampusMitra – RAG Chatbot for University Student Queries

A Flask web application that answers student questions using uploaded university PDF/TXT documents. It follows the project synopsis workflow:

1. PDF/TXT text extraction
2. Character chunking (500 characters, 50 overlap)
3. `all-MiniLM-L6-v2` sentence-transformer embeddings
4. FAISS vector index (NumPy cosine-search fallback if FAISS cannot be installed)
5. Top-4 semantic retrieval
6. Context-restricted Gemini answer generation (optional API key)
7. Source document and chunk references
8. Refusal when retrieved evidence is insufficient
9. Evaluation using a sample question set

## 1. Requirements

- Windows 10/11, macOS or Linux
- Python 3.10–3.12 recommended (Python 3.11 is a good choice)
- 8 GB RAM recommended
- Internet connection on first run to install packages and download the embedding model
- GPU is not required

**Important:** Python 3.13/3.14 may not have compatible wheels for every ML dependency. If installation fails, install Python 3.11 (64-bit) and create the environment with `py -3.11 -m venv .venv`.

## 2. Run on Windows (recommended)

1. Extract the ZIP file.
2. Open the extracted `CampusMitra` folder in VS Code.
3. Open Terminal → New Terminal (PowerShell).
4. Run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

If PowerShell blocks activation, run this once in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

5. Open `http://127.0.0.1:5000` in Chrome.
6. Open **Knowledge documents** and upload your university PDF/TXT files.
7. Ask questions in the chat.

Alternative: double-click `run_windows.bat`. It creates a virtual environment, installs dependencies and starts the application. It assumes the Python launcher can find Python 3.11 or another installed Python 3 version.

## 3. Gemini API (optional)

The application works without an API key. Without Gemini it returns the most relevant retrieved document passage and clearly labels it as a retrieval fallback.

To enable generated answers:

1. Create a Gemini API key from Google AI Studio.
2. Open `.env` in the project folder.
3. Add:

```env
GEMINI_API_KEY=PASTE_YOUR_API_KEY_HERE
GEMINI_MODEL=gemini-2.0-flash
```

4. Stop and restart `python app.py`.

Never upload or commit your `.env` file or share your API key. Model names and API availability can change; if the configured Gemini model is unavailable, the application falls back to retrieved evidence.

## 4. Project structure

```text
CampusMitra/
├── app.py
├── run.py
├── run_windows.bat
├── requirements.txt
├── .env.example
├── README.md
├── campusmitra/
│   ├── __init__.py
│   ├── config.py
│   ├── ingestion.py
│   ├── vector_store.py
│   ├── rag.py
│   └── evaluation.py
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── data/
│   ├── documents/       # Uploaded and sample PDF/TXT documents
│   └── index/           # Generated FAISS index, vectors and metadata
└── evaluation/
    └── test_questions.csv
```

## 5. Included demonstration documents

The `data/documents` folder contains sample university information for testing. These are fictional demonstration policies and dates, not official Dayananda Sagar University rules. Delete or replace them with authorized official documents before demonstrating the system as a university information assistant.

## 6. Evaluation

Open the **Evaluation** tab and click **Run evaluation**. The included CSV has sample questions and expected answers. The application reports:
- Keyword coverage as a rough correctness proxy
- Percentage of responses with retrieved source evidence
- Average response time

These are preliminary automated indicators, not validated research accuracy scores. For your final academic evaluation, manually label the 25–30 questions, record correct/incorrect answers, inspect citations, and report the measurement method.

## 7. Troubleshooting

### `py` does not recognize Python 3.11
Install Python 3.11 (64-bit), enable “Add Python to PATH”, reopen VS Code, then run `py -3.11 --version`.

### `faiss` installation fails
The project includes a NumPy cosine-similarity fallback. If the FAISS package is unavailable, the application can still run semantic retrieval, but the vector search is not using FAISS. For the synopsis requirement, use an environment where `faiss-cpu` installs successfully and verify the FAISS package is active.

### First request is slow
The first request that needs embeddings downloads and loads `all-MiniLM-L6-v2`. Later requests use the cached model.

### PDF uploads but no text is found
Scanned/image-only PDFs need OCR before this version can extract their text. Use a text-based PDF or convert/OCR the scan first.

### Port 5000 is already in use
Close the other Flask process or change the port in the final `app.run(...)` line of `app.py`.

## 8. API routes

- `GET /api/status` – index and model status
- `GET /api/documents` – indexed document list
- `POST /api/upload` – upload and index a PDF/TXT file (`file` form field)
- `POST /api/chat` – ask a question (`{"question":"..."}`)
- `POST /api/rebuild` – rebuild index from files in `data/documents`
- `POST /api/evaluate` – run the bundled evaluation set

## 9. Academic implementation notes

The implementation uses CPU embeddings, normalized vectors and inner-product search (equivalent to cosine similarity for normalized vectors). The retriever returns up to four chunks. A similarity threshold is used as a conservative evidence gate; tune and validate it against a labelled question set before reporting results. A hosted LLM is optional and only receives the retrieved text and question. The system prompt explicitly limits answers to the retrieved context and asks for source filenames.
