"""Anthropic Claude 호출 래퍼. 프로바이더 교체 시 이 파일만 바꾸면 된다."""
import os
from functools import lru_cache

from .config import MODEL


@lru_cache(maxsize=1)
def _client():
    from anthropic import Anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 환경변수가 필요합니다. .env.example을 복사해 설정하세요."
        )
    return Anthropic(api_key=key)


def complete(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """단일 턴 프롬프트 → 텍스트 응답."""
    msg = _client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")
