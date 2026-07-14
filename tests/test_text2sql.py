"""LLM 없이 검증 가능한 SQL 안전성 가드 테스트."""
from src.text2sql import is_safe


def test_allows_select():
    assert is_safe("SELECT * FROM datasets")
    assert is_safe("  select mrr from experiment_results where mrr > 0.8  ")
    assert is_safe("WITH t AS (SELECT 1) SELECT * FROM t")


def test_blocks_mutations():
    assert not is_safe("DROP TABLE datasets")
    assert not is_safe("DELETE FROM experiments")
    assert not is_safe("UPDATE datasets SET name='x'")
    assert not is_safe("INSERT INTO datasets VALUES (9,'x','ko',1,1,'x')")


def test_blocks_multi_statement():
    assert not is_safe("SELECT 1; DELETE FROM datasets")
