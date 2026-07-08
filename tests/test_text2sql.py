"""LLM 없이 검증 가능한 순수 로직 테스트 (SQL 안전성 가드)."""
from src.text2sql import is_safe


def test_allows_select():
    assert is_safe("SELECT * FROM sites")
    assert is_safe("  select progress_pct from progress where progress_pct < 50  ")
    assert is_safe("WITH t AS (SELECT 1) SELECT * FROM t")


def test_blocks_mutations():
    assert not is_safe("DROP TABLE sites")
    assert not is_safe("DELETE FROM floors")
    assert not is_safe("UPDATE sites SET name='x'")
    assert not is_safe("INSERT INTO sites VALUES (9,'x','y','z')")


def test_blocks_multi_statement():
    assert not is_safe("SELECT 1; DELETE FROM sites")
