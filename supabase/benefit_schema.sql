-- ============================================================
-- 하나FIT 청년 혜택 DB 스키마
-- Supabase SQL Editor에 그대로 붙여넣기
-- ============================================================

-- pgvector 확장 (이미 활성화돼 있으면 무시됨)
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 0. updated_at 자동 갱신 트리거 함수
-- ============================================================
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = timezone('utc', now());
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 1. organizations — 제공처 (소관기관)
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
  id         SERIAL PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,   -- 소관기관명
  phone      TEXT,                   -- 문의 전화번호
  created_at TIMESTAMPTZ DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ DEFAULT timezone('utc', now())
);

CREATE OR REPLACE TRIGGER trg_organizations_updated_at
  BEFORE UPDATE ON organizations
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMENT ON TABLE  organizations         IS '혜택 제공 소관기관';
COMMENT ON COLUMN organizations.name    IS '소관기관명 (예: 보건복지부)';
COMMENT ON COLUMN organizations.phone   IS '문의 전화번호';


-- ============================================================
-- 2. benefits — 혜택 본문
-- ============================================================
CREATE TABLE IF NOT EXISTS benefits (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id          INT  REFERENCES organizations(id) ON DELETE SET NULL,

  -- 기본 정보
  service_name             TEXT NOT NULL,          -- 서비스명
  support_type             TEXT,                   -- 지원유형 (현금/현물/서비스)
  ai_summary               TEXT,                   -- AI요약
  service_field            TEXT,                   -- 서비스분야

  -- 자격/선정
  target_users             TEXT,                   -- 지원대상
  selection_criteria       TEXT,                   -- 선정기준

  -- 지원 내용
  support_content          TEXT,                   -- 지원내용

  -- 신청 정보
  application_method       TEXT,                   -- 신청방법
  application_period_start DATE,                   -- 신청기간 시작일
  application_period_end   DATE,                   -- 신청기간 종료일
  application_period_text  TEXT,                   -- 신청기간 원문 ("상시" 등)
  is_always_open           BOOLEAN DEFAULT false,  -- 상시 모집 여부
  required_documents       TEXT,                   -- 구비서류
  application_url          TEXT,                   -- 신청 URL

  -- 링크
  detail_url               TEXT,                   -- 상세 URL (정보제공URL)
  external_site_url        TEXT,                   -- 관련 외부 사이트 URL

  -- 원본 연결
  source_service_id        TEXT UNIQUE,            -- 정부24 원본 서비스ID

  created_at               TIMESTAMPTZ DEFAULT timezone('utc', now()),
  updated_at               TIMESTAMPTZ DEFAULT timezone('utc', now())
);

CREATE OR REPLACE TRIGGER trg_benefits_updated_at
  BEFORE UPDATE ON benefits
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 자주 필터링될 컬럼 인덱스
CREATE INDEX IF NOT EXISTS idx_benefits_service_field     ON benefits (service_field);
CREATE INDEX IF NOT EXISTS idx_benefits_is_always_open    ON benefits (is_always_open);
CREATE INDEX IF NOT EXISTS idx_benefits_organization_id   ON benefits (organization_id);
CREATE INDEX IF NOT EXISTS idx_benefits_source_service_id ON benefits (source_service_id);

COMMENT ON TABLE  benefits                        IS '청년 혜택 서비스 본문';
COMMENT ON COLUMN benefits.source_service_id      IS '정부24 서비스ID — 원본 API 연동용';
COMMENT ON COLUMN benefits.application_period_text IS '"상시", "2024-03-01 ~ 2024-04-30" 등 원문 보존';
COMMENT ON COLUMN benefits.ai_summary             IS 'GPT가 생성한 한 줄 요약';


-- ============================================================
-- 3. benefit_user_types — 사용자구분 (M:N)
--    한 혜택에 청년·구직자·1인가구 등 복수 대상 가능
-- ============================================================
CREATE TABLE IF NOT EXISTS benefit_user_types (
  id         SERIAL PRIMARY KEY,
  benefit_id UUID NOT NULL REFERENCES benefits(id) ON DELETE CASCADE,
  user_type  TEXT NOT NULL,
  UNIQUE (benefit_id, user_type)
);

CREATE INDEX IF NOT EXISTS idx_benefit_user_types_user_type
  ON benefit_user_types (user_type);

COMMENT ON TABLE  benefit_user_types           IS '혜택-사용자구분 매핑 (M:N)';
COMMENT ON COLUMN benefit_user_types.user_type IS '청년 / 장애인 / 1인가구 / 구직자 ...';


-- ============================================================
-- 4. benefit_chunks — 벡터 임베딩
--    서비스 1개당 4개 청크 (summary / eligibility / content / application)
-- ============================================================
CREATE TABLE IF NOT EXISTS benefit_chunks (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  benefit_id UUID NOT NULL REFERENCES benefits(id) ON DELETE CASCADE,

  -- 청크 종류
  -- 'summary'     : 서비스명 + 분야 + 대상 + AI요약          → 추천·검색용
  -- 'eligibility' : 서비스명 + 지원대상 + 선정기준            → 자격 확인용
  -- 'content'     : 서비스명 + 지원유형 + 지원내용            → 혜택 내용 확인용
  -- 'application' : 서비스명 + 신청방법 + 기간 + 서류 + URL  → 신청 안내용
  chunk_type TEXT NOT NULL
    CHECK (chunk_type IN ('summary', 'eligibility', 'content', 'application')),

  chunk_text TEXT NOT NULL,          -- 임베딩에 사용된 원문 텍스트
  embedding  vector(1536),           -- text-embedding-3-small 기준

  created_at TIMESTAMPTZ DEFAULT timezone('utc', now())
);

-- HNSW 인덱스 — 정밀도·속도 균형 (데이터 insert 완료 후 생성 권장)
CREATE INDEX IF NOT EXISTS idx_benefit_chunks_embedding
  ON benefit_chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- chunk_type별 조회용 인덱스
CREATE INDEX IF NOT EXISTS idx_benefit_chunks_type
  ON benefit_chunks (chunk_type);

COMMENT ON TABLE  benefit_chunks            IS '혜택 RAG용 벡터 임베딩 청크';
COMMENT ON COLUMN benefit_chunks.chunk_type IS 'summary | eligibility | content | application';
COMMENT ON COLUMN benefit_chunks.chunk_text IS '임베딩 생성 시 사용한 실제 텍스트 (재현·디버깅용)';
COMMENT ON COLUMN benefit_chunks.embedding  IS 'pgvector 1536차원 (text-embedding-3-small)';


-- ============================================================
-- 5. match_benefits — RAG 유사도 검색 함수
--    benefits + organizations 정보를 JOIN해서 한 번에 반환
-- ============================================================
CREATE OR REPLACE FUNCTION match_benefits(
  query_embedding  vector(1536),
  filter_chunk_type TEXT    DEFAULT NULL,   -- NULL이면 전체 chunk_type 검색
  match_threshold  FLOAT   DEFAULT 0.5,
  match_count      INT     DEFAULT 5
)
RETURNS TABLE (
  -- 청크 정보
  chunk_id        UUID,
  chunk_type      TEXT,
  chunk_text      TEXT,
  similarity      FLOAT,
  -- 혜택 본문
  benefit_id      UUID,
  service_name    TEXT,
  support_type    TEXT,
  ai_summary      TEXT,
  service_field   TEXT,
  target_users    TEXT,
  selection_criteria TEXT,
  support_content TEXT,
  application_method TEXT,
  application_period_text TEXT,
  is_always_open  BOOLEAN,
  required_documents TEXT,
  application_url TEXT,
  detail_url      TEXT,
  external_site_url TEXT,
  -- 제공처
  org_name        TEXT,
  org_phone       TEXT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    bc.id                         AS chunk_id,
    bc.chunk_type,
    bc.chunk_text,
    1 - (bc.embedding <=> query_embedding) AS similarity,
    b.id                          AS benefit_id,
    b.service_name,
    b.support_type,
    b.ai_summary,
    b.service_field,
    b.target_users,
    b.selection_criteria,
    b.support_content,
    b.application_method,
    b.application_period_text,
    b.is_always_open,
    b.required_documents,
    b.application_url,
    b.detail_url,
    b.external_site_url,
    o.name  AS org_name,
    o.phone AS org_phone
  FROM benefit_chunks bc
  JOIN benefits      b  ON b.id  = bc.benefit_id
  LEFT JOIN organizations o ON o.id = b.organization_id
  WHERE
    (filter_chunk_type IS NULL OR bc.chunk_type = filter_chunk_type)
    AND bc.embedding IS NOT NULL
    AND 1 - (bc.embedding <=> query_embedding) > match_threshold
  ORDER BY bc.embedding <=> query_embedding
  LIMIT match_count;
$$;

COMMENT ON FUNCTION match_benefits IS
  'RAG 유사도 검색 — benefit_chunks + benefits + organizations JOIN 반환.
   filter_chunk_type: NULL(전체) | summary | eligibility | content | application';


-- ============================================================
-- 6. get_benefit_user_types — 혜택별 사용자구분 배열 조회 함수
-- ============================================================
CREATE OR REPLACE FUNCTION get_benefit_user_types(p_benefit_id UUID)
RETURNS TEXT[]
LANGUAGE sql STABLE
AS $$
  SELECT array_agg(user_type ORDER BY user_type)
  FROM benefit_user_types
  WHERE benefit_id = p_benefit_id;
$$;
