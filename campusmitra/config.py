from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "documents"
INDEX_DIR = DATA_DIR / "index"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K = 4
# Retrieval similarity below this value is treated as insufficient evidence.
MIN_SIMILARITY = 0.25
ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_UPLOAD_MB = 20
