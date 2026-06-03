# 하나청년 챗봇 — FastAPI AI 서버 설계

## 전체 아키텍처

Spring Boot + FastAPI 이중 서버 구조에서 **FastAPI는 AI 처리 전담 서비스**다.
Spring Boot가 프론트엔드 API, 인증, 세션, 채팅 히스토리, 혜택 CRUD를 담당하고,
FastAPI는 Spring Boot에서 내부 호출을 받아 의도 분류 → RAG → 응답 생성을 수행한 뒤
구조화된 결과를 돌려준다.

```
Frontend → Spring Boot → FastAPI (AI) → Supabase pgvector / OpenAI
                 ↕
              PostgreSQL / Redis
```

---

## 역할 분담

| FastAPI가 하는 것 | Spring Boot가 하는 것 |
|---|---|
| 의도 분류 (LLM) | 인증 / 세션 관리 |
| RAG (벡터 검색 + 응답 생성) | 채팅 히스토리 저장 |
| 혜택 카드 생성 | 혜택 CRUD (일반 DB) |
| 예상 질문 생성 | 프론트엔드 REST API |
| Supabase pgvector 쿼리 | 유저 프로필 관리 |

FastAPI는 **무상태(stateless)** — 세션/히스토리는 Spring Boot가 넘겨준다.

---

## 기술 스택

| 레이어 | 선택 |
|---|---|
| 백엔드 프레임워크 | Python 3.11 + FastAPI |
| AI 오케스트레이션 | LangChain |
| LLM | GPT-4o (OpenAI) |
| 벡터 DB | Supabase pgvector |
| 구조화 출력 | OpenAI Structured Outputs (response_format) |
| 임베딩 모델 | text-embedding-3-small |

---

## 의도 분류 (3종)

| intent | 설명 |
|---|---|
| `text_rag` | 벡터 검색 후 RAG 응답 |
| `text_simple` | LLM 직접 응답 (인사, 간단한 질문) |
| `benefit_cards` | 혜택 카드 목록 반환 |

> `suggested_questions`(예상 질문)는 독립 intent가 아닌 **모든 응답에 항상 포함**되는 필드로 처리.

---

## API 엔드포인트

### 1. 채팅 처리 (핵심)

```
POST /api/v1/chat/process
```

Spring Boot가 컨텍스트를 조립해서 호출한다.

**Request**
```json
{
  "message": "string",
  "chat_history": [
    { "role": "user | assistant", "content": "string" }
  ],
  "user_profile": {
    "age": 25,
    "income_percentile": 50,
    "region": "서울",
    "employment_status": "재직 | 구직 | 학생"
  }
}
```

**Response**
```json
{
  "intent": "text_rag | text_simple | benefit_cards",
  "text": "string",
  "benefit_cards": [
    {
      "id": "string",
      "title": "string",
      "summary": "string",
      "amount": "string",
      "target": "string",
      "deadline": "string | null",
      "link": "string | null"
    }
  ],
  "suggested_questions": ["string", "string", "string"],
  "citations": [
    { "source": "string", "snippet": "string" }
  ],
  "extracted_user_info": {
    "age": "number | null",
    "region": "string | null"
  }
}
```

> `extracted_user_info`: LLM이 발화에서 자동 추출한 프로필 정보.
> Spring Boot가 수신 후 유저 프로필에 머지해서 저장한다.
> `benefit_cards`, `citations`는 해당 intent가 아닐 경우 null.

---

### 2. 혜택 대상자 체크

```
POST /api/v1/benefits/eligibility
```

**Request**
```json
{
  "benefit_id": "string",
  "benefit_content": "string",
  "user_profile": { "..." }
}
```

> `benefit_content`: Spring Boot가 DB에서 조회한 혜택 내용 텍스트를 그대로 넘긴다.

**Response**
```json
{
  "eligible": true,
  "reason": "만 19~34세 청년, 소득 기준 충족",
  "estimated_amount": "최대 월 50만원 | null"
}
```

---

### 3. 벡터 검색 (디버그/테스트용)

```
POST /api/v1/rag/search
```

**Request**
```json
{
  "query": "string",
  "top_k": 5
}
```

**Response**
```json
{
  "documents": [
    { "id": "string", "content": "string", "score": 0.92 }
  ]
}
```

---

### 4. 헬스체크

```
GET /health   →   { "status": "ok" }
```

---

## 내부 처리 흐름 (POST /api/v1/chat/process)

```
1. Intent 분류
   └─ OpenAI Structured Output
   └─ 출력: { intent, extracted_user_info }

2. intent별 분기
   ├─ text_rag:
   │   ├─ message 임베딩 → Supabase pgvector 유사도 검색
   │   ├─ 검색 결과를 컨텍스트로 주입
   │   └─ LLM 응답 생성 (with citations)
   │
   ├─ text_simple:
   │   └─ LLM 직접 호출 (chat_history 포함)
   │
   └─ benefit_cards:
       ├─ user_profile 기반 pgvector 필터 검색
       └─ 카드 형태로 포맷

3. suggested_questions 생성
   └─ LLM + Structured Output → 3개 반환

4. 결과 조립 후 반환
```

---

## 파일 구성

```
fastapi-server/
├── app/
│   ├── main.py                       # FastAPI 앱 초기화, 라우터 등록, 헬스체크
│   ├── exceptions.py                 # 커스텀 예외 정의
│   ├── api/
│   │   └── v1/
│   │       ├── chat.py               # POST /chat/process
│   │       ├── benefits.py           # POST /benefits/eligibility
│   │       └── rag.py                # POST /rag/search
│   ├── services/
│   │   ├── intent.py                 # 의도 분류 (Structured Output)
│   │   ├── chat.py                   # 채팅 응답 생성 (simple / rag)
│   │   ├── rag.py                    # RAG 프롬프트 조립 (구현 예정)
│   │   ├── benefit_card.py           # 혜택 카드 생성 (구현 예정)
│   │   ├── eligibility.py            # 대상자 체크 (구현 예정)
│   │   └── suggestion.py             # 예상 질문 생성
│   ├── repositories/
│   │   └── vector.py                 # pgvector DB 쿼리 전담 (RAG용)
│   ├── clients/
│   │   ├── openai.py                 # OpenAI AsyncClient 초기화
│   │   └── supabase.py               # Supabase Client 초기화
│   ├── schemas/
│   │   ├── chat.py                   # ChatProcessRequest / ChatProcessResponse
│   │   ├── benefit.py                # BenefitCard, EligibilityRequest/Response
│   │   └── rag.py                    # RagSearchRequest/Response
│   ├── dependencies/
│   │   └── common.py                 # FastAPI DI 함수 모음
│   ├── middlewares/
│   │   └── logging.py                # 요청/응답 로깅 미들웨어
│   └── core/
│       ├── config.py                 # pydantic-settings (env vars)
│       └── prompts/
│           ├── intent.py             # 의도 분류 프롬프트
│           ├── chat.py               # 채팅 응답 프롬프트
│           └── suggestion.py         # 예상 질문 생성 프롬프트
├── supabase/
│   └── init.sql                      # pgvector 테이블 및 함수 초기화 SQL
├── tests/
│   ├── test_health.py
│   ├── test_chat.py
│   └── test_rag.py
├── requirements.txt
└── .env.example
```

---

## 주요 환경변수

```
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
EMBED_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o
```

---

## 미결 사항

- **유저 프로필 전략**: 대화 중 LLM 자동 추출 vs 프론트 명시적 입력 — 현재 양쪽 모두 지원 방향
- **AI 모델 선택 근거**: GPT-4o 외 Claude / Gemini 비교 검토 필요
