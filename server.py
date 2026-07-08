"""Ask-My-Data MCP 서버 엔트리포인트.

노출 도구:
  - ask(question)            : 질문을 자동 라우팅해 종합 답변 (Multi-Agent)
  - search_documents(query)  : 비정형 문서 의미 검색 (RAG)
  - query_stats(question)    : 정형 데이터 자연어 집계 (Text2SQL)
"""
from mcp.server.fastmcp import FastMCP

from src.graph import run_pipeline
from src import rag, text2sql

mcp = FastMCP("ask-my-data")


@mcp.tool()
def ask(question: str) -> str:
    """자연어 질문을 RAG(문서)/Text2SQL(데이터)로 자동 라우팅해 종합 답변합니다."""
    return run_pipeline(question)


@mcp.tool()
def search_documents(query: str) -> str:
    """비정형 문서에서 의미 기반으로 관련 내용을 검색합니다 (RAG)."""
    hits = rag.search(query)
    if not hits:
        return "검색 결과가 없습니다."
    return "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)


@mcp.tool()
def query_stats(question: str) -> str:
    """정형 데이터(SQLite)에 자연어 집계 질의를 수행합니다 (Text2SQL)."""
    sql, rows = text2sql.query(question)
    body = "\n".join(str(r) for r in rows) if rows else "(결과 없음)"
    return f"-- SQL\n{sql}\n\n-- 결과\n{body}"


if __name__ == "__main__":
    mcp.run()
