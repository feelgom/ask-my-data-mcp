"""완전 합성 검색 평가 데이터로 sample.db를 생성한다.

이름, 설명, 수치는 검색/RAG 실험을 위해 임의로 만든 예시이며
특정 회사, 고객, 서비스 또는 실제 실험 결과를 나타내지 않는다.

    python data/build_sample_db.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "sample.db"

SCHEMA = """
CREATE TABLE datasets (
    dataset_id    INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    language      TEXT NOT NULL,
    query_count   INTEGER NOT NULL,
    document_count INTEGER NOT NULL,
    description   TEXT NOT NULL
);

CREATE TABLE experiments (
    experiment_id INTEGER PRIMARY KEY,
    dataset_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    retriever     TEXT NOT NULL,
    top_k         INTEGER NOT NULL,
    precision_at_5 REAL NOT NULL,
    recall_at_10   REAL NOT NULL,
    mrr             REAL NOT NULL,
    ndcg_at_10      REAL NOT NULL,
    latency_ms      REAL NOT NULL,
    run_date        TEXT NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE VIEW experiment_results AS
SELECT d.name          AS dataset_name,
       d.language      AS language,
       e.name          AS experiment_name,
       e.retriever     AS retriever,
       e.top_k         AS top_k,
       e.precision_at_5 AS precision_at_5,
       e.recall_at_10   AS recall_at_10,
       e.mrr             AS mrr,
       e.ndcg_at_10      AS ndcg_at_10,
       e.latency_ms      AS latency_ms,
       e.run_date        AS run_date
FROM experiments e
JOIN datasets d ON d.dataset_id = e.dataset_id;
"""

DATASETS = [
    (1, "Orbit Support KR", "ko", 60, 320, "합성 한국어 도움말 문서와 질문"),
    (2, "Atlas Catalog EN", "en", 80, 500, "합성 영문 상품 카탈로그와 탐색 질의"),
    (3, "Mosaic Notes Multilingual", "ko+en", 50, 240, "합성 한영 연구 노트와 다국어 질의"),
]

# 모든 수치는 검색 평가 예제를 위해 임의로 구성했다.
# (id, dataset_id, name, retriever, top_k, p@5, r@10, mrr, ndcg@10, latency_ms, date)
EXPERIMENTS = [
    (1, 1, "orbit-bm25", "BM25", 10, 0.72, 0.68, 0.76, 0.74, 18.4, "2026-06-01"),
    (2, 1, "orbit-dense", "Dense", 10, 0.75, 0.76, 0.79, 0.78, 42.7, "2026-06-02"),
    (3, 1, "orbit-hybrid", "Hybrid-RRF", 10, 0.82, 0.84, 0.86, 0.85, 55.2, "2026-06-03"),
    (4, 2, "atlas-bm25", "BM25", 10, 0.78, 0.71, 0.80, 0.77, 20.1, "2026-06-04"),
    (5, 2, "atlas-dense", "Dense", 10, 0.81, 0.80, 0.84, 0.83, 45.8, "2026-06-05"),
    (6, 2, "atlas-hybrid", "Hybrid-RRF", 10, 0.86, 0.87, 0.89, 0.88, 59.4, "2026-06-06"),
    (7, 3, "mosaic-bm25", "BM25", 10, 0.65, 0.61, 0.69, 0.66, 17.9, "2026-06-07"),
    (8, 3, "mosaic-dense", "Dense", 10, 0.77, 0.79, 0.81, 0.80, 48.6, "2026-06-08"),
    (9, 3, "mosaic-hybrid", "Hybrid-RRF", 10, 0.83, 0.86, 0.87, 0.86, 62.3, "2026-06-09"),
]


def build_database(path: Path = DB) -> Path:
    """지정한 경로에 합성 검색 실험 DB를 새로 만든다."""
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO datasets VALUES (?,?,?,?,?,?)", DATASETS)
        con.executemany("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?)", EXPERIMENTS)
        con.commit()
    finally:
        con.close()
    return path


def main():
    path = build_database()
    print(f"생성 완료: {path}")
    con = sqlite3.connect(path)
    try:
        for row in con.execute(
            "SELECT dataset_name, experiment_name, ndcg_at_10, latency_ms "
            "FROM experiment_results ORDER BY ndcg_at_10 DESC LIMIT 3"
        ):
            print("  nDCG@10 상위:", row)
    finally:
        con.close()


if __name__ == "__main__":
    main()
