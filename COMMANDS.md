# 하나청년 챗봇 AI 서버 - 명령어 정리

## 설치

```bash
pip install -r requirements.txt
```

## 서버 실행

```bash
# 개발 모드 (코드 변경 시 자동 재시작)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 테스트

```bash
pytest tests/
```

## API 문서 (서버 실행 후 브라우저에서 접속)

| 주소 | 설명 |
|------|------|
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | 헬스 체크 |

## 주요 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | /api/v1/chat | 챗봇 대화 |
| GET/POST | /api/v1/benefits | 혜택 카드 조회 |
| GET/POST | /api/v1/rag | RAG 검색 |

## 환경 변수 (.env 파일)

```env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```
