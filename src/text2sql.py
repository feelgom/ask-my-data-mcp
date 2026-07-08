"""Text2SQL 노드 — 자연어 → 검증된 SELECT → 실행.

안전장치: SELECT/WITH 로 시작하는 단일 문만 허용, 변경 계열 키워드 차단.
"""
import re
import sqlite3
from functools import lru_cache

from .config import DB_PATH
from .llm import complete

_FORBIDDEN = re.compile(
    r"\b(drop|delete|update|insert|alter|create|replace|attach|pragma)\b", re.I
)


@lru_cache(maxsize=1)
def _schema() -> str:
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type IN ('table','view') AND sql NOT NULL"
        ).fetchall()
        return "\n".join(r[0] for r in rows)
    finally:
        con.close()


def is_safe(sql: str) -> bool:
    """읽기 전용 단일 SELECT 인지 검증."""
    s = sql.strip().rstrip(";")
    if ";" in s:                      # 다중 문 차단
        return False
    if not s.lower().startswith(("select", "with")):
        return False
    if _FORBIDDEN.search(s):
        return False
    return True


def generate_sql(question: str) -> str:
    prompt = (
        "아래 SQLite 스키마를 참고해 질문에 답하는 SQL을 작성하세요.\n"
        "SELECT 문 하나만 작성하고, 코드펜스나 설명 없이 SQL만 출력하세요.\n\n"
        f"스키마:\n{_schema()}\n\n"
        f"질문: {question}\n\nSQL:"
    )
    sql = complete(prompt, max_tokens=300).strip()
    # 혹시 남은 코드펜스 제거
    sql = re.sub(r"^```\w*", "", sql).strip()
    sql = re.sub(r"```$", "", sql).strip()
    return sql


def run(sql: str):
    con = sqlite3.connect(DB_PATH)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        con.close()


def query(question: str):
    """(sql, rows) 반환. 안전하지 않거나 실패하면 rows에 error 담아 반환."""
    sql = generate_sql(question)
    if not is_safe(sql):
        return sql, [{"error": "안전하지 않은 쿼리로 판단되어 실행하지 않았습니다."}]
    try:
        return sql, run(sql)
    except Exception as exc:  # 잘못된 컬럼 등
        return sql, [{"error": str(exc)}]
