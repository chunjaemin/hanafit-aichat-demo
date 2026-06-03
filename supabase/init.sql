-- pgvector 확장 활성화
create extension if not exists vector;

-- RAG용 문서 테이블
create table if not exists documents (
    id uuid default gen_random_uuid() primary key,
    content text not null,
    embedding vector(1536),
    metadata jsonb default '{}',
    source text,
    created_at timestamp with time zone default timezone('utc', now())
);

-- 유사도 검색 인덱스 (코사인 거리 기반 IVFFlat)
create index if not exists documents_embedding_idx
    on documents using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- 유사도 검색 함수
create or replace function match_documents(
    query_embedding vector(1536),
    match_threshold float default 0.7,
    match_count int default 5
)
returns table (
    id uuid,
    content text,
    metadata jsonb,
    source text,
    similarity float
)
language sql stable
as $$
    select
        id,
        content,
        metadata,
        source,
        1 - (embedding <=> query_embedding) as similarity
    from documents
    where 1 - (embedding <=> query_embedding) > match_threshold
    order by embedding <=> query_embedding
    limit match_count;
$$;
