# Ask-My-Data MCP

> 하나의 자연어 질문을 **의미 검색(RAG)** 과 **데이터 집계(Text2SQL)** 경로로 자동 라우팅해 답하는 MCP 서버.
> LangGraph 기반 Multi-Agent 파이프라인 데모 — "디지털 트윈을 자연어로 질의한다"는 아이디어를 **공개·가상 데이터**로 재현한 포트폴리오 프로젝트입니다.

## 실행 증거

아래 이미지는 2026-07-14에 클린 가상환경에서 MCP stdio 연결 후 `tools/list`와
`search_documents`를 실제 호출한 결과입니다.

![Ask-My-Data MCP smoke test](assets/mcp-smoke-test.png)

| 검증 | 결과 |
|---|---|
| `pip install -e ".[dev]"` | 통과 (Python 3.14.5) |
| `python -m pytest -q` | 3 passed |
| MCP initialize · tools/list | 통과 — 3 tools |
| `search_documents` 호출 | 통과 — API 키 없이 BM25 검색 |

`ask`와 `query_stats`는 라우팅·SQL 생성·답변 합성에 Claude를 사용하므로
`ANTHROPIC_API_KEY`가 필요합니다. 위 smoke test는 키나 외부 API 없이 검증 가능한 검색 경로입니다.

## 무엇을 보여주나
- **MCP 서버** — 범용 LLM 클라이언트(Claude Desktop 등)에서 도구로 호출
- **Multi-Agent 라우팅** — 질문 유형(`semantic`/`structured`/`both`)을 판단해 경로 분기
- **RAG** — BM25 키워드 + (옵션)다국어 임베딩 Hybrid Search
- **Text2SQL** — 자연어 → 검증된 SELECT → 집계
- **Synthesize** — 근거 기반 한국어 답변 생성

## 아키텍처

```
          ┌──────────┐
질문 ────▶ │  Router  │  semantic / structured / both 분류
          └────┬─────┘
       ┌───────┼────────┐
       ▼                ▼
  ┌─────────┐     ┌───────────┐
  │  RAG    │     │ Text2SQL  │
  │ (문서)   │     │ (SQLite)  │
  └────┬────┘     └─────┬─────┘
       └────────┬───────┘         (both: RAG → Text2SQL 순으로 이어붙임)
                ▼
         ┌────────────┐
         │ Synthesize │  근거 종합 → 자연어 답변
         └────────────┘
```

## 빠른 시작

```bash
# 1) 설치
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"         # 기본 + 테스트
pip install -e ".[embeddings]"   # 옵션: 다국어 임베딩 Hybrid Search

# 2) 환경변수
cp .env.example .env             # ANTHROPIC_API_KEY 채우기
export $(cat .env | xargs)       # 또는 direnv/python-dotenv

# 3) 샘플 데이터 생성 (가상 건설 현장)
python data/build_sample_db.py

# 4) MCP 없이 바로 테스트 (CLI)
python -m src.cli "진척률이 뭐야?"
python -m src.cli "송도 C현장 3층 진척률 몇 %야?"
python -m src.cli "진척률이 가장 낮은 층은 어디고, 진척률은 어떻게 계산해?"

# 단위 테스트
python -m pytest -q
```

## MCP 클라이언트에 연결 (Claude Desktop 예시)

`claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ask-my-data": {
      "command": "python",
      "args": ["/absolute/path/to/ask-my-data-mcp/server.py"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```
노출 도구: `ask` (자동 라우팅) · `search_documents` (RAG) · `query_stats` (Text2SQL)

## 예시 질문과 라우팅
| 질문 | 라우팅 | 경로 |
|---|---|---|
| "진척률이 뭐야?" | semantic | RAG |
| "강남 A현장 3층 진척률?" | structured | Text2SQL |
| "진척률 낮은 현장은 왜 낮고, 진척률은 어떻게 계산돼?" | both | RAG + Text2SQL |

## 데이터에 관하여
`data/` 의 모든 데이터는 **가상**입니다. 실제 회사/고객 데이터가 아닙니다.
스키마: `sites`(현장) · `floors`(층별 계획/설치 요소 수) · `progress`(진척률 뷰).

## 기술 스택
`Python` · `MCP` · `LangGraph` · `Anthropic Claude` · `rank-bm25` · `sentence-transformers(옵션)` · `SQLite`

## 관련 글
- [블로그 1편] 디지털 트윈에게 말을 걸다 — MCP 서버를 0→1로
- [블로그 2편] 하나의 프롬프트로는 안 됐다 — LangGraph Multi-Agent 라우팅

## 라이선스
MIT
