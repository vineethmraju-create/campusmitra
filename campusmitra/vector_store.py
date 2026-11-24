import json
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

from campusmitra.config import INDEX_DIR, MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
from campusmitra.ingestion import extract_document, chunk_text

class VectorStore:
    """Persistent semantic search. Uses FAISS when available, NumPy cosine search otherwise."""
    def __init__(self):
        self.model = None
        self.records = []
        self.matrix = None
        self.index = None
        self.faiss = None
        self._load_faiss()
        self._load_saved()

    def _load_faiss(self):
        try:
            import faiss
            self.faiss = faiss
        except Exception:
            self.faiss = None

    def _get_model(self):
        if self.model is None:
            print(f"Loading embedding model: {MODEL_NAME} (first run may download model files)...")
            self.model = SentenceTransformer(MODEL_NAME, device="cpu")
        return self.model

    def _embed(self, texts):
        vectors = self._get_model().encode(
            texts, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False
        )
        return np.asarray(vectors, dtype="float32")

    def _load_saved(self):
        metadata_path = INDEX_DIR / "chunks.json"
        vectors_path = INDEX_DIR / "vectors.npy"
        if metadata_path.exists() and vectors_path.exists():
            try:
                self.records = json.loads(metadata_path.read_text(encoding="utf-8"))
                self.matrix = np.load(vectors_path).astype("float32")
                self._build_index()
            except Exception:
                self.records, self.matrix, self.index = [], None, None

    def _build_index(self):
        self.index = None
        if self.faiss is not None and self.matrix is not None and len(self.matrix):
            self.index = self.faiss.IndexFlatIP(self.matrix.shape[1])
            self.index.add(self.matrix)

    def _save(self):
        (INDEX_DIR / "chunks.json").write_text(
            json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if self.matrix is not None:
            np.save(INDEX_DIR / "vectors.npy", self.matrix)
        self._build_index()

    def add_document(self, filename, text):
        pieces = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not pieces:
            raise ValueError("The document did not contain usable text.")
        # Replace older chunks for a document with the same name.
        keep = [r for r in self.records if r["source"] != filename]
        old_count = len(self.records) - len(keep)
        new_records = [
            {"source": filename, "chunk_id": i + 1, "text": piece}
            for i, piece in enumerate(pieces)
        ]
        new_vectors = self._embed([r["text"] for r in new_records])
        if keep:
            keep_indices = [i for i, r in enumerate(self.records) if r["source"] != filename]
            old_vectors = self.matrix[keep_indices]
            self.matrix = np.vstack([old_vectors, new_vectors]).astype("float32")
        else:
            self.matrix = new_vectors
        self.records = keep + new_records
        self._save()
        return len(pieces)

    def rebuild_from_folder(self, folder: Path):
        self.records = []
        self.matrix = None
        self.index = None
        files = sorted(list(folder.glob("*.pdf")) + list(folder.glob("*.txt")))
        for path in files:
            text = extract_document(path)
            pieces = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
            if not pieces:
                continue
            new_records = [{"source": path.name, "chunk_id": i + 1, "text": p}
                           for i, p in enumerate(pieces)]
            vectors = self._embed([r["text"] for r in new_records])
            self.records.extend(new_records)
            self.matrix = vectors if self.matrix is None else np.vstack([self.matrix, vectors])
        if self.matrix is None:
            self.matrix = np.empty((0, 384), dtype="float32")
        self._save()
        return len({r["source"] for r in self.records})

    def search(self, question, top_k=TOP_K):
        if not self.records or self.matrix is None or len(self.matrix) == 0:
            return []
        query_vector = self._embed([question])
        if self.index is not None:
            scores, indices = self.index.search(query_vector, min(top_k, len(self.records)))
            pairs = [(int(i), float(s)) for i, s in zip(indices[0], scores[0]) if i >= 0]
        else:
            scores = np.dot(self.matrix, query_vector[0])
            indices = np.argsort(scores)[::-1][:top_k]
            pairs = [(int(i), float(scores[i])) for i in indices]
        return [
            {**self.records[i], "score": score}
            for i, score in pairs
        ]

    def is_ready(self):
        return bool(self.records)

    def document_count(self):
        return len({r["source"] for r in self.records})

    def chunk_count(self):
        return len(self.records)

    def list_documents(self):
        summary = {}
        for record in self.records:
            summary[record["source"]] = summary.get(record["source"], 0) + 1
        return [{"filename": name, "chunks": count} for name, count in sorted(summary.items())]
