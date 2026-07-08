"""Router 노드 — 질문을 처리 경로로 분류한다.

경계 사례에서 확신이 낮으면 안전하게 'both'로 폴백(틀리느니 둘 다 시도).
"""
from .llm import complete

_SYSTEM = """당신은 사용자 질문을 처리 경로로 분류하는 라우터입니다.

- semantic  : 개념/정의/설명/절차 등 문서 기반 질문
              예) "진척률이 뭐야?", "시공 판단은 어떻게 해?"
- structured: 수치/집계/목록 등 데이터베이스 조회 질문
              예) "3층 진척률 몇 %야?", "현장별 평균 진척률 알려줘"
- both      : 위 둘이 모두 필요한 복합 질문
              예) "진척률이 낮은 현장은 어디고, 진척률은 어떻게 계산돼?"

정확히 semantic, structured, both 중 하나만 소문자로 답하세요. 다른 말은 하지 마세요."""


def route(question: str) -> str:
    resp = complete(question, system=_SYSTEM, max_tokens=8).strip().lower()
    if "both" in resp:
        return "both"
    if "struct" in resp:
        return "structured"
    if "semantic" in resp:
        return "semantic"
    # 파싱 실패 시 안전하게 둘 다 시도
    return "both"
