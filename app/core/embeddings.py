import hashlib
import time

import numpy as np
from google.genai import types

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.models import EmbeddingDB


def text_hash(text: str) -> str:
    """Cache key: model, size aur text teeno badlein to naya embedding banta hai."""
    raw = f"{settings.embedding_model}|{settings.embedding_dim}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize(vectors) -> np.ndarray:
    """Har vector ki lambai 1 kar deta hai, taake dot product = cosine similarity."""
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def embed_batch(
    texts: list[str], client, task_type: str, batch_size: int = 50, delay: float = 0.0
) -> list[list[float]]:
    """Texts ko batches me Gemini se embed karwata hai."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        response = client.models.embed_content(
            model=settings.embedding_model,
            contents=chunk,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dim,
            ),
        )
        chunk_vectors = [list(e.values) for e in response.embeddings]
        if len(chunk_vectors) != len(chunk):
            raise ValueError("Embedding API ne texts se kam vectors wapis diye")
        vectors.extend(chunk_vectors)
        if delay and start + batch_size < len(texts):
            time.sleep(delay)
    return vectors


def embed_query(text: str, client) -> np.ndarray:
    return normalize(embed_batch([text], client, "RETRIEVAL_QUERY"))[0]


def embed_documents_cached(
    texts: list[str], client, batch_size: int = 50, delay: float = 1.0
) -> np.ndarray:
    """Documents ke normalized vectors. Jo pehle embed ho chuke wo DB cache se aate hain."""
    init_db()
    keys = [text_hash(t) for t in texts]

    cached: dict[str, np.ndarray] = {}
    with SessionLocal() as session:
        for i in range(0, len(keys), 500):
            rows = (
                session.query(EmbeddingDB)
                .filter(EmbeddingDB.text_hash.in_(keys[i : i + 500]))
                .all()
            )
            for row in rows:
                cached[row.text_hash] = np.frombuffer(row.vector, dtype=np.float32)

    missing: dict[str, str] = {}
    for key, text in zip(keys, texts):
        if key not in cached and key not in missing:
            missing[key] = text

    if missing:
        print(f"[INFO] {len(missing)} naye documents embed ho rahe hain (sirf pehli baar)...")
        items = list(missing.items())
        for start in range(0, len(items), batch_size):
            chunk = items[start : start + batch_size]
            vectors = embed_batch([t for _, t in chunk], client, "RETRIEVAL_DOCUMENT", batch_size=batch_size)
            with SessionLocal() as session:  # har batch ke baad save, taake kaam zaya na ho
                for (key, _), vec in zip(chunk, vectors):
                    arr = np.asarray(vec, dtype=np.float32)
                    session.add(
                        EmbeddingDB(text_hash=key, model=settings.embedding_model, vector=arr.tobytes())
                    )
                    cached[key] = arr
                session.commit()
            if delay and start + batch_size < len(items):
                time.sleep(delay)

    return normalize([cached[k] for k in keys])
