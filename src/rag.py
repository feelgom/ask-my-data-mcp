"""RAG 노드 — BM25 키워드 검색 + (옵션) 다국어 임베딩 Hybrid Search."""
import re
from functools import lru_cache

import numpy as np

from .config import DOCS_DIR

_TOKEN = re.compile(r"[가-힣]+|[a-zA-Z]+|\d+")


def _tok(text: str):
    return _TOKEN.findall(text.lower())


@lru_cache(maxsize=1)
def _corpus():
    """docs/*.md 를 빈 줄 기준 문단 청크로 분할."""
    chunks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for para in re.split(r"\n\s*\n", text):
            para = para.strip()
            if len(para) > 15:
                chunks.append({"source": path.name, "text": para})
    return chunks


@lru_cache(maxsize=1)
def _bm25():
    from rank_bm25 import BM25Okapi

    return BM25Okapi([_tok(c["text"]) for c in _corpus()])


@lru_cache(maxsize=1)
def _embedder():
    """설치돼 있으면 다국어 임베딩 모델, 없으면 None (BM25 전용)."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    except Exception:
        return None


def _norm(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr, dtype=float)
    return arr / arr.max() if arr.size and arr.max() > 0 else arr


def search(query: str, k: int = 3):
    """관련 청크 상위 k개를 {source, text, score}로 반환."""
    corpus = _corpus()
    if not corpus:
        return []

    scores = _norm(_bm25().get_scores(_tok(query)))

    embedder = _embedder()
    if embedder is not None:
        from sentence_transformers import util

        q_vec = embedder.encode(query, convert_to_tensor=True)
        d_vec = embedder.encode([c["text"] for c in corpus], convert_to_tensor=True)
        sim = util.cos_sim(q_vec, d_vec).cpu().numpy().ravel()
        scores = 0.5 * scores + 0.5 * _norm(sim)  # Hybrid

    top = scores.argsort()[::-1][:k]
    return [{**corpus[i], "score": round(float(scores[i]), 3)} for i in top]
