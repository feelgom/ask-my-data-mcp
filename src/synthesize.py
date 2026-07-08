"""Synthesize 노드 — 검색·조회 근거를 종합해 한국어 답변 생성."""
from .llm import complete


def synthesize(question: str, route: str, retrieved: list, rows: list) -> str:
    parts = []
    if retrieved:
        parts.append(
            "[문서 검색 결과]\n"
            + "\n".join(f"- ({r['source']}) {r['text']}" for r in retrieved)
        )
    if rows:
        parts.append("[데이터 조회 결과]\n" + "\n".join(str(r) for r in rows))
    context = "\n\n".join(parts) if parts else "(근거 없음)"

    prompt = (
        "사용자 질문에 아래 근거만 사용해 한국어로 간결하게 답하세요.\n"
        "근거가 부족하면 모른다고 답하고 추측하지 마세요.\n\n"
        f"질문: {question}\n\n{context}\n\n답변:"
    )
    return complete(prompt, max_tokens=600).strip()
