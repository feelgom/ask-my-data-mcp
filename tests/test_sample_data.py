"""합성 검색 실험 데이터와 BM25 검색 경로를 검증한다."""
import sqlite3

from data.build_sample_db import build_database
from src import rag


def test_builds_search_experiment_database(tmp_path):
    db = build_database(tmp_path / "sample.db")
    con = sqlite3.connect(db)
    try:
        dataset_count = con.execute("SELECT COUNT(*) FROM datasets").fetchone()[0]
        experiment_count = con.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
        best = con.execute(
            "SELECT experiment_name FROM experiment_results ORDER BY ndcg_at_10 DESC LIMIT 1"
        ).fetchone()[0]
    finally:
        con.close()

    assert dataset_count == 3
    assert experiment_count == 9
    assert best == "atlas-hybrid"


def test_bm25_finds_metric_definition(monkeypatch):
    rag._corpus.cache_clear()
    rag._bm25.cache_clear()
    monkeypatch.setattr(rag, "_embedder", lambda: None)

    hits = rag.search("MRR 첫 번째 관련 문서 순위", k=1)

    assert hits[0]["source"] == "metrics.md"
    assert "MRR" in hits[0]["text"]


def test_bm25_separates_collaboration_topic(monkeypatch):
    rag._corpus.cache_clear()
    rag._bm25.cache_clear()
    monkeypatch.setattr(rag, "_embedder", lambda: None)

    hits = rag.search("OT CRDT 동시 편집 수렴", k=1)

    assert hits[0]["source"] == "realtime_collaboration_ot_crdt.md"
