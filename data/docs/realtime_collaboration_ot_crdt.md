# 실시간 협업 편집 - OT vs CRDT (Google Docs, Notion, Figma)

> 실시간 동시 편집의 두 축은 OT(중앙 서버가 연산을 변환)와 CRDT(자료구조 자체가 수렴을 보장)이며, 실제 프로덕션(Figma, Notion)은 "중앙 서버 + Last-Writer-Wins"라는 더 단순한 제3의 길을 택한 경우가 많다.

## Overview

여러 사람이 같은 문서를 동시에 고칠 때의 핵심 문제는 **"동시에 발생한 편집을 어떻게 충돌 없이 하나의 상태로 수렴시키는가"**다. 학계와 업계의 대표 답은 두 가지다:

1. **OT (Operational Transformation)** — 1989년 Ellis & Gibbs가 제안. 모든 편집을 연산(op)으로 표현하고, 동시 연산이 도착하면 서로의 위치를 **변환(transform)** 해서 적용한다. 중앙 서버가 순서를 정해주는 구조가 사실상 전제. Google Docs가 대표 사례 [1][2][3].
2. **CRDT (Conflict-free Replicated Data Type)** — 2011년 Shapiro 등이 정식화. 자료구조 자체를 수학적으로 설계(가환성, semilattice)해서 **어떤 순서로 병합해도 같은 결과로 수렴**하도록 보장. 중앙 서버가 필요 없어 오프라인/P2P/local-first에 적합. Yjs, Automerge가 대표 구현 [4][5].

그런데 실제 제품을 뜯어보면 **Figma와 Notion은 둘 다 교과서적 OT도, 완전한 CRDT도 아니다.** 중앙 서버가 있다는 사실을 이용해 훨씬 단순한 방식(속성/블록 단위 Last-Writer-Wins + 연산 로그)을 쓴다. "두 가지 방식"은 이론의 양대 축이고, 실무는 그 사이 어딘가에 있다.

---

## Key Findings

### 1. OT의 동작 원리와 Google Docs

**핵심 아이디어**: 문서를 스냅샷이 아니라 **연산의 로그**로 저장하고, 동시 연산이 겹치면 위치를 보정한다.

Google Docs 엔지니어(John Day-Richter)가 2010년 공식 블로그에 직접 공개한 내용 [2][3]:

- 모든 편집은 3가지 연산으로 환원된다: `InsertText`, `DeleteText`, `ApplyStyle`. 문서는 이 연산들의 **revision log**이고, 화면 표시는 로그를 처음부터 replay해서 만든다. 예: `{InsertText 'T' @10}`
- **변환(transform)의 예**: 내가 위치 1에 "IT" 2글자를 삽입한 상태에서, 상대방의 `{DeleteText @9-11}`이 도착하면 그대로 적용할 수 없다(엉뚱한 글자가 지워짐). 상대 연산을 내 로컬 상태 기준으로 변환해야 한다. `{ApplyStyle bold @10-20}`을 `{InsertText 'ABC' @15}`에 대해 변환하면 `{ApplyStyle Bold @10-23}`이 되는 식.
- 변환 함수는 **모든 연산 쌍의 조합**(Insert×Delete, Insert×Style, ...)에 대해 정의되어야 한다. "OT가 올바르게 구현되면, 모든 편집자가 모든 변경을 수신한 시점에 전원이 동일한 문서를 보게 됨"이 수렴 보장.
- **프로토콜은 중앙집중식(Jupiter 모델)**: 클라이언트는 4가지 상태(마지막 서버 리비전, 미전송 로컬 변경, 전송했지만 미확인된 변경, 현재 문서)를 유지하고, 서버는 pending 큐 + 전체 revision log를 유지한다 [3].
- Google Wave의 OT 백서(Wang, Mah, Lassen)는 이를 더 단순화: **클라이언트는 서버의 ACK를 받기 전까지 다음 연산을 보내지 않는다.** 덕분에 서버는 클라이언트별 상태 공간 없이 단일 연산 히스토리만 유지하면 된다. 대기 중 로컬 연산들은 compose해서 하나로 합쳐 보낸다 [6].

**OT의 약점**: 변환 함수의 조합 폭발과 정확성 증명이 극도로 어렵다. ShareJS 저자이자 전 Wave 엔지니어 Joseph Gentle: "OT 구현은 끔찍하다(implementing OT sucks). 알고리즘이 정말 어렵고 올바르게 구현하는 데 시간이 많이 든다" [7]. 특히 서버 없이 분산 OT를 하려던 Wave 페더레이션은 실패 사례로 회고된다 [8].

### 2. CRDT의 동작 원리와 현대 구현

**핵심 아이디어**: 변환 로직 대신 **자료구조 자체가 수렴을 보장**하게 설계한다.

- Shapiro et al. 2011 논문이 정식화: Strong Eventual Consistency(SEC) 하에서 수렴 조건을 만족하는 타입이 CRDT. "복제본은 어떤 수의 장애에도 불구하고 자가 안정적으로 수렴함이 보장된다" [4].
- 두 가지 형태(수학적으로 동치):
  - **State-based (CvRDT)**: 상태가 monotonic semilattice를 이루고, merge는 least upper bound.
  - **Op-based (CmRDT)**: 동시 연산끼리 가환(commutative)이어야 하며, 인과적 전달을 전제.
- **텍스트 CRDT의 실제 구현(Yjs)** [5]: 삽입되는 모든 요소에 고유 ID `(clientID, clock)`(Lamport timestamp)를 부여. 삭제된 요소는 실제로 지우지 않고 **tombstone**(삭제 플래그)으로 남긴다. 동시 삽입의 순서는 각 아이템의 `origin`/`originRight` 참조로 결정(YATA 알고리즘).
- **성능은 더 이상 결정적 약점이 아니다**: Yjs는 연속 타이핑을 하나의 Item으로 병합해 메타데이터가 문자 수가 아닌 연산 수에 비례한다. 26만 편집 실측 트레이스에서 Item 객체 10,971개, 메모리 19.7MB, 파싱 20ms [9]. Joseph Gentle의 벤치마크에서는 같은 트레이스에 Automerge(당시 JS 버전) 291초/880MB vs Yjs 0.97초/3.3MB vs 자신의 Rust 구현(diamond-types) 0.056초 — "5000배 차이". 결론: **알고리즘 선택보다 구현 품질이 지배적** [10].
- 단, "CRDT는 잘못 구현하기 쉽다"(Kleppmann). Logoot/LSEQ 계열은 동시 삽입 시 글자가 뒤섞이는 interleaving 결함이 있고, RGA/YATA는 이를 회피한다. 트리 이동(move) 연산은 별도 연구가 필요했던 난제 [11].

### 3. Figma — "CRDT에서 영감을 받은" 중앙집중 LWW

Figma 공동창업자 Evan Wallace의 2019년 공식 기술 블로그 [12]:

- **OT 기각 이유**: 디자인 툴에는 "불필요하게 복잡"하고, 가능한 상태의 조합 폭발 때문에 추론이 어렵다.
- **완전한 CRDT 기각 이유**: CRDT의 분산 합의 오버헤드는 서버가 없을 때 필요한 것인데, **Figma는 서버가 중앙 권위자**이므로 그 오버헤드를 제거하고 "더 빠르고 가벼운 구현"을 택했다.
- **실제 방식**:
  - 문서 = 객체 트리(각 객체는 key-value 속성). 클라이언트는 문서별 서버 프로세스에 WebSocket으로 연결.
  - 충돌 해소 = **객체의 속성(property) 단위 Last-Writer-Wins**. 같은 속성을 동시에 고치면 "서버에 마지막으로 도착한 값"이 이긴다. 서로 다른 속성(한 명은 색, 한 명은 위치)을 고치면 둘 다 보존 — 이게 문자 단위 병합이 필요 없는 디자인 툴의 특성과 맞아떨어진다.
  - 클라이언트는 ACK 전의 로컬 변경을 서버 업데이트보다 우선 표시하는 **클라이언트 사이드 예측**으로 즉각적인 UX를 만든다.
  - 자식 순서는 **fractional indexing**: 위치를 0과 1 사이의 분수로 표현해, 재정렬 충돌 없이 두 값 사이에 끼워넣는다. 부모 링크는 자식 쪽 속성으로 저장해 reparenting 시 객체 identity를 보존.
- HN 커뮤니티(268pt 스레드)에서는 "신뢰할 수 있는 서버가 있으니 CRDT보다 효율적으로 만들 수 있다는 게 요지"라는 요약과, "그래도 표준 CRDT를 썼어야 했다"는 반론(gun.js 저자 등)이 공존 [13].

### 4. Notion — OT도 CRDT도 아닌 트랜잭션 로그

Notion 공식 엔지니어링 블로그(2021, Jake Teton-Landis) [14]:

- **모든 것이 블록(block)**: 텍스트, 이미지, DB row, 페이지까지 전부 `id + type + properties + content(자식 ID 배열) + parent` 구조. 들여쓰기조차 스타일이 아니라 렌더 트리의 구조다.
- **협업 방식**: 사용자 편집은 단일 레코드를 생성/수정하는 **operation**이 되고, 이들이 **transaction**으로 묶여 클라이언트 `TransactionQueue`(IndexedDB/SQLite에 영속화)에 쌓인다. 서버의 `saveTransactions` 엔드포인트가 권한·정합성을 검증한 뒤 **원자적으로 커밋 또는 거부**한다. 변경 전파는 MessageStore(WebSocket 서비스) → 알림받은 클라이언트가 `syncRecordValues`로 최신 레코드를 다시 가져와 렌더.
- 즉 **문자 단위 병합(OT/CRDT convergence)이 없다.** 충돌 단위가 블록(레코드)이라서, 같은 블록에 두 명이 동시에 타이핑하면 덮어쓰기가 발생할 수 있다 — Notion에서 같은 문단 동시 편집이 Google Docs만큼 매끄럽지 않은 이유. (⚠️ 이 마지막 특성은 공식 설명에서 도출한 추론)
- 저장 계층: 블록 테이블을 workspace ID 기준 480 논리 샤드 / Postgres 32대(이후 96대)로 샤딩 [15].

### 5. OT vs CRDT — 근본 트레이드오프

| 축 | OT | CRDT |
|---|---|---|
| 수렴 방식 | 변환 함수가 연산 위치를 보정 | 자료구조가 수학적으로 수렴 보장 |
| 중앙 서버 | 사실상 필수 (순서 결정자) | 불필요 (P2P/오프라인 가능) |
| 복잡성의 위치 | 변환 함수의 조합 폭발, 정확성 증명 | 요소별 고유 ID + tombstone 메타데이터 |
| 메모리/문서 크기 | 로그 압축 가능, 오버헤드 작음 | 과거엔 심각, 현대 구현(Yjs)은 ~53% 오버헤드 수준 [9] |
| 강점 시나리오 | 중앙 서버가 보장된 문자 단위 텍스트 편집 | local-first, 오프라인 장기 분기, P2P, 서버 없는 병합 |
| 대표 사례 | Google Docs, CodeMirror 협업 모듈 | Yjs(ProseMirror/CodeMirror/Monaco 바인딩), Automerge |

전문가 진영의 결론이 갈린 지점:

- **Gentle (2020) "I was wrong. CRDTs are the future"**: 10년간 OT를 만들던 그가 입장을 뒤집음. 현대 CRDT는 성능 문제가 해결됐고(log n 조회, columnar encoding으로 오버헤드 1.5~2배), "OT가 가진 모든 기능은 CRDT에 넣을 수 있지만 그 역은 안 된다" [8].
- **Haverbeke (CodeMirror 6, 2020)**: 반대로 "아주 지루한 비분산 OT"를 의도적으로 선택. 중앙 서버가 변경을 직렬화하면 변환 증명이 사실상 필요 없어지고, 거대 문서 지원과 깔끔한 API에 유리 [16].
- **학계**: OT 진영(Sun et al. 2018)은 "CRDT의 우월성 주장을 반박한다"는 논문을 냈다 — 다만 저자가 OT 연구자라 당파적이며, "CRDT는 실제 협업 편집기에서 드물다"는 주장은 이후 Yjs의 광범위한 채택으로 낡은 이야기가 됐다 [17].

---

## Contradictions & Open Questions

- **Notion = CRDT?**: 서드파티 시스템 디자인 블로그들은 "Notion이 CRDT(Yjs)를 쓴다"고 서술하지만 [18], Notion **공식** 엔지니어링 블로그는 트랜잭션 로그 + 서버 검증 방식만을 설명한다 [14]. Tier 1 우선 원칙에 따라 공식 설명을 채택. 서드파티 글들은 근거 없는 재구성으로 보인다. (2021년 이후 내부적으로 바뀌었을 가능성은 배제 못 하나, 공개된 1차 소스는 없음)
- **OT vs CRDT 우열 논쟁은 미해결**: Gentle은 "CRDT가 미래"라 하고, Haverbeke와 Sun은 반박한다. 같은 HN 스레드에서도 "극단적 주장"이라는 비판이 있었고 Gentle 본인도 일부 인정 [19]. 데이터 모델과 배포 형태(서버 유무)에 따라 답이 달라지는 문제이지, 절대 승자는 없다.
- **CRDT의 실전 함정 (커뮤니티 보고)**: Yjs는 스키마 불일치 시 조용한 데이터 손실이 전 피어로 전파된 사례, 권한 시스템(Editor/Viewer) 구현의 어려움, JS 중심(UTF-16) 생태계로 인한 타 언어 백엔드 구축 곤란이 보고됨 [20][21]. Automerge는 대형 문서에서 OOM 이슈가 여럿 보고됨(670KB 문서 로드에 ~500MB RAM 등, 이후 버전에서 일부 개선) [22].

## Practical Insights

**"어떤 방식을 쓸까"의 실질적 결정 트리:**

1. **중앙 서버가 항상 있고, 문자 단위 텍스트 병합이 필요한가?** → 서버 직렬화 기반 OT가 가장 단순하고 검증됐다 (Google Docs, CodeMirror 방식). 서버가 순서를 정해주면 OT의 어려운 부분(변환 증명)이 대부분 사라진다.
2. **데이터가 텍스트 스트림이 아니라 객체/블록인가?** → 굳이 OT/CRDT가 필요 없을 수 있다. 속성 단위 LWW(Figma) 또는 레코드 단위 트랜잭션(Notion)이 훨씬 단순하다. **충돌의 최소 단위를 데이터 모델에 맞게 정하는 것**이 알고리즘 선택보다 중요하다.
3. **오프라인 우선, P2P, 서버 없는 병합이 요구사항인가?** → CRDT가 사실상 유일한 답. 직접 구현하지 말고 검증된 라이브러리를 쓸 것 — 텍스트/리치텍스트는 **Yjs**(성능, 에디터 바인딩 풍부), Git 같은 브랜치/히스토리가 제품 요구면 **Automerge**, 성능 극한이면 Loro 같은 신생 옵션 [21].
4. **공통 교훈**:
   - 어느 쪽이든 자체 구현은 최후의 수단. OT는 변환 정확성, CRDT는 잘못 만들기 쉬운 알고리즘(interleaving 결함)이 지뢰다 [11].
   - 순서 재정렬 충돌에는 Figma의 **fractional indexing** 패턴이 범용적으로 유용하다 (Jira 랭킹 등에서도 동일 패턴 사용).
   - UX의 체감 속도는 알고리즘이 아니라 **클라이언트 사이드 예측**(로컬 선반영 + 서버 확정)에서 나온다.
   - 대부분의 앱은 "트랜잭션이 지배적이고 협업은 얇은 한 조각"이므로, 협업이 필요한 부분에만 국소적으로 적용하라는 실무 조언도 있다 [19].

## Sources

### Tier 1 — Official

- [1] [Ellis & Gibbs, "Concurrency Control in Groupware Systems"](https://dl.acm.org/doi/10.1145/67544.66963) - OT 원조 논문, dOPT 알고리즘 (1989)
- [2] [What's different about the new Google Docs: Conflict resolution](https://drive.googleblog.com/2010/09/whats-different-about-new-google-docs_22.html) - Google Docs OT 공식 설명 3부작, 본문은 [UW PDF 미러](https://idl.uw.edu/future-scholarly-communication/files/2010-GoogleDocs-OT.pdf)로 검증 (2010-09-22)
- [3] [What's different about the new Google Docs: Making collaboration fast](https://drive.googleblog.com/2010/09/whats-different-about-new-google-docs_23.html) - 클라이언트 4-상태/서버 프로토콜 (2010-09-23)
- [4] [Shapiro et al., "Conflict-free Replicated Data Types" (SSS 2011)](https://www.lip6.fr/Marc.Shapiro/papers/2011/CRDTs_SSS-2011.pdf) - CRDT 정식화, SEC 수렴 증명 (2011)
- [5] [Yjs INTERNALS.md](https://github.com/yjs/yjs/blob/main/INTERNALS.md) - Lamport timestamp ID, tombstone, integrate 알고리즘 (현행)
- [6] [Google Wave Operational Transformation whitepaper](https://svn.apache.org/repos/asf/incubator/wave/whitepapers/operational-transform/operational-transform.html) - ACK 대기 방식으로 서버 상태 단순화 (2009-2010)
- [12] [How Figma's multiplayer technology works](https://www.figma.com/blog/how-figmas-multiplayer-technology-works/) - Evan Wallace, 속성 단위 LWW + fractional indexing (2019-10-16)
- [14] [The data model behind Notion's flexibility](https://www.notion.com/blog/data-model-behind-notion) - 블록 모델, TransactionQueue, saveTransactions, MessageStore (2021-05-18)
- [15] [Sharding Postgres at Notion](https://www.notion.com/blog/sharding-postgres-at-notion) - 480 논리 샤드 (2021-10)
- [17] [Sun et al., "Real Differences between OT and CRDT for Co-Editors"](https://arxiv.org/abs/1810.02137) - OT 진영의 CRDT 반박 논문 (2018-10)

### Tier 2 — Expert

- [7] [ShareJS](https://sharejs.org/) - Joseph Gentle, "implementing OT sucks" (~2011)
- [8] [I was wrong. CRDTs are the future](https://josephg.com/blog/crdts-are-the-future/) - Gentle의 OT→CRDT 전향 선언 (2020-09-26)
- [9] [Are CRDTs suitable for shared editing?](https://blog.kevinjahns.de/are-crdts-suitable-for-shared-editing/) - Yjs 저자의 실측 벤치마크, 26만 op → 19.7MB (2020-08-10)
- [10] [5000x faster CRDTs: An Adventure in Optimization](https://josephg.com/blog/crdts-go-brrr/) - Automerge 291s vs diamond-types 0.056s (2021-07-31)
- [11] [CRDTs: The Hard Parts](https://martin.kleppmann.com/2020/07/06/crdt-hard-parts-hydra.html) - Kleppmann, interleaving 결함·트리 이동 난제 (2020-07-06)
- [16] [Collaborative Editing in CodeMirror](https://marijnhaverbeke.nl/blog/collaborative-editing-cm.html) - Haverbeke의 의도적 OT 선택 (2020-05-14)
- [20] [Lies I was Told About Collaborative Editing, Pt. 2: Why we don't use Yjs](https://www.moment.dev/blog/lies-i-was-told-pt-2) - Yjs 실전 함정(데이터 손실, 권한, 디버깅) (2024~)

### Tier 3 — Community

- [13] [HN: How Figma's multiplayer technology works](https://news.ycombinator.com/item?id=21378858) - 268pt, CRDT 진영 반론 포함 (2019-10)
- [18] [howworks.ai: How Notion was built](https://howworks.ai/blog/how-notion-was-built) - ⚠️ "Notion=CRDT" 주장하는 서드파티 재구성, 공식 소스와 충돌 (2025~)
- [19] [HN: I was wrong. CRDTs are the future](https://news.ycombinator.com/item?id=31049883) - 241pt, "극단적 주장" 반박과 저자 인정 (2022-04)
- [21] [HN: Yjs vs Automerge 비교 스레드](https://news.ycombinator.com/item?id=41012895) - "기본은 Yjs, 히스토리 필요하면 Automerge" (2024)
- [22] [Automerge GitHub #1231, #705, #896](https://github.com/automerge/automerge/issues/1231) - 대형 문서 OOM 보고 (2022-2023)
- [23] [How I reverse engineered Google Docs](https://features.jsomers.net/how-i-reverse-engineered-google-docs/) - revision log 실증(키스트로크 replay) (2014)

---
_Last researched: 2026-07-13 (deep-research 3-tier)_
