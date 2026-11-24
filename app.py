import os
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from campusmitra.config import BASE_DIR, UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_MB
from campusmitra.ingestion import extract_document
from campusmitra.vector_store import VectorStore
from campusmitra.rag import answer_question
from campusmitra.evaluation import run_evaluation

load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
store = VectorStore()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({
        "ready": store.is_ready(),
        "document_count": store.document_count(),
        "chunk_count": store.chunk_count(),
        "llm_enabled": bool(os.getenv("GEMINI_API_KEY")),
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
    })

@app.route("/api/documents")
def documents():
    return jsonify({"documents": store.list_documents()})

@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Please select a PDF or TXT file."}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF and TXT files are supported."}), 400

    filename = secure_filename(file.filename)
    destination = UPLOAD_DIR / filename
    # Avoid overwriting a different document with the same name.
    if destination.exists():
        stem, suffix = destination.stem, destination.suffix
        counter = 2
        while (UPLOAD_DIR / f"{stem}_{counter}{suffix}").exists():
            counter += 1
        destination = UPLOAD_DIR / f"{stem}_{counter}{suffix}"

    file.save(destination)
    try:
        text = extract_document(destination)
        if len(text.strip()) < 30:
            destination.unlink(missing_ok=True)
            return jsonify({"error": "No readable text was found. If this is a scanned PDF, run OCR first."}), 400
        chunks_added = store.add_document(destination.name, text)
        return jsonify({
            "message": f"{destination.name} uploaded and indexed successfully.",
            "filename": destination.name,
            "chunks_added": chunks_added
        })
    except Exception as exc:
        destination.unlink(missing_ok=True)
        app.logger.exception("Document ingestion failed")
        return jsonify({"error": f"Could not process document: {exc}"}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Enter a question first."}), 400
    if len(question) > 1000:
        return jsonify({"error": "Please keep the question under 1,000 characters."}), 400
    started = time.perf_counter()
    try:
        result = answer_question(question, store)
        result["response_time_seconds"] = round(time.perf_counter() - started, 3)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Chat request failed")
        return jsonify({"error": f"Unable to answer right now: {exc}"}), 500

@app.route("/api/rebuild", methods=["POST"])
def rebuild():
    try:
        count = store.rebuild_from_folder(UPLOAD_DIR)
        return jsonify({"message": "Knowledge base rebuilt successfully.", "documents": count,
                        "chunks": store.chunk_count()})
    except Exception as exc:
        app.logger.exception("Index rebuild failed")
        return jsonify({"error": str(exc)}), 500

@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    try:
        result = run_evaluation(store)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Evaluation failed")
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    print("\nCampusMitra is starting...")
    print("Open http://127.0.0.1:5000 in your browser.")
    app.run(host="127.0.0.1", port=5000, debug=True)
