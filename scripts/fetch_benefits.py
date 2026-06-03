#!/usr/bin/env python3
"""
정부24 청년 혜택 데이터 수집 파이프라인
- 정부24 API → benefits DB + pgvector 임베딩 한 번에 처리
- 중복(source_service_id 기준) skip
- 실행: python -m scripts.fetch_benefits  (fastapi-server/ 디렉토리에서)
"""

import asyncio
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import create_client, Client

# ── 환경변수 로드 ─────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── 설정 ──────────────────────────────────────────────────────────────────────
def _require(key: str) -> str:
    val = os.getenv(key, "")
    if not val:
        log.error(f".env에 {key}가 없습니다.")
        sys.exit(1)
    return val

OPENAI_API_KEY = _require("OPENAI_API_KEY")
SUPABASE_URL   = _require("SUPABASE_URL")
SUPABASE_KEY   = _require("SUPABASE_KEY")
GOV24_API_KEY  = _require("GOV24_API_KEY")   # data.go.kr Decoding 키

GOV24_URL      = "https://api.odcloud.kr/api/gov24/v3/serviceList"
EMBED_MODEL    = os.getenv("EMBED_MODEL", "text-embedding-3-small")
FETCH_LIMIT    = int(os.getenv("FETCH_LIMIT", "100"))   # 가져올 최대 건수
EMBED_BATCH    = 100                                     # 임베딩 배치 크기


# ── 1. 정부24 API 호출 ────────────────────────────────────────────────────────
def _is_youth(svc: dict) -> bool:
    """서비스명·지원대상·서비스목적요약 중 하나라도 '청년'이 포함되면 청년 서비스로 판별"""
    fields = ('서비스명', '지원대상', '서비스목적요약')
    return any('청년' in (svc.get(f) or '') for f in fields)


async def fetch_youth_services() -> list[dict]:
    """
    페이지를 순회하며 청년 관련 서비스를 FETCH_LIMIT건 수집.
    사용자구분 필드는 '개인'/'가구' 대분류라 청년 판별 불가 →
    서비스명·지원대상·서비스목적요약 키워드로 필터링.
    """
    collected: list[dict] = []
    page = 1
    per_page = 100
    max_pages = 20  # 최대 2000건 조회 후 중단

    log.info(f"정부24 API 페이지 순회 시작 (청년 서비스 {FETCH_LIMIT}건 목표)...")

    async with httpx.AsyncClient(timeout=30) as client:
        while len(collected) < FETCH_LIMIT and page <= max_pages:
            url = (
                f"{GOV24_URL}"
                f"?serviceKey={quote(GOV24_API_KEY, safe='')}"
                f"&page={page}"
                f"&perPage={per_page}"
                f"&returnType=JSON"
            )
            res = await client.get(url)
            res.raise_for_status()
            body = res.json()

            items = body.get("data", [])
            if not items:
                log.info("더 이상 데이터 없음. 순회 종료.")
                break

            youth = [s for s in items if _is_youth(s)]
            collected.extend(youth)
            log.info(
                f"  페이지 {page}: {len(items)}건 조회 → 청년 {len(youth)}건 "
                f"(누적 {len(collected)}건)"
            )

            if len(items) < per_page:  # 마지막 페이지
                break
            page += 1

    result = collected[:FETCH_LIMIT]
    log.info(f"청년 서비스 수집 완료: {len(result)}건")
    return result


# ── 2. 청크 텍스트 생성 ───────────────────────────────────────────────────────
def _line(label: str, value: str | None) -> str:
    return f"[{label}] {value.strip()}\n" if value and value.strip() else ""

def build_chunks(svc: dict, user_types: str) -> dict[str, str]:
    """서비스 1개 → 4개 청크 텍스트 (빈 필드는 라인 생략)"""
    return {
        "summary": (
            _line("서비스명",   svc.get("서비스명"))
            + _line("서비스분야", svc.get("서비스분야"))
            + _line("지원유형",  svc.get("지원유형"))
            + _line("사용자구분", user_types)
            + _line("요약",     svc.get("서비스목적요약"))
        ).strip(),

        "eligibility": (
            _line("서비스명",   svc.get("서비스명"))
            + _line("지원대상",  svc.get("지원대상"))
            + _line("선정기준",  svc.get("선정기준"))
            + _line("사용자구분", user_types)
        ).strip(),

        "content": (
            _line("서비스명",  svc.get("서비스명"))
            + _line("지원유형", svc.get("지원유형"))
            + _line("지원내용", svc.get("지원내용"))
        ).strip(),

        "application": (
            _line("서비스명",  svc.get("서비스명"))
            + _line("신청방법", svc.get("신청방법"))
            + _line("신청기간", svc.get("신청기한"))
            + _line("구비서류", svc.get("구비서류"))
            + _line("신청URL",  svc.get("온라인신청URL") or svc.get("상세조회URL"))
        ).strip(),
    }


# ── 3. 임베딩 배치 생성 ───────────────────────────────────────────────────────
async def embed_texts(openai: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    results: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i : i + EMBED_BATCH]
        log.info(f"  임베딩 배치 {i+1}~{i+len(batch)} / {len(texts)}")
        res = await openai.embeddings.create(model=EMBED_MODEL, input=batch)
        results.extend(e.embedding for e in res.data)
    return results


# ── 4. DB 헬퍼 ────────────────────────────────────────────────────────────────
def already_imported(db: Client, source_id: str) -> bool:
    res = db.table("benefits").select("id").eq("source_service_id", source_id).execute()
    return bool(res.data)

def get_or_create_org(db: Client, name: str, phone: str | None) -> int:
    res = db.table("organizations").select("id").eq("name", name).execute()
    if res.data:
        return res.data[0]["id"]
    ins = db.table("organizations").insert({"name": name, "phone": phone}).execute()
    return ins.data[0]["id"]

def insert_benefit(db: Client, svc: dict, org_id: int) -> str:
    row = {
        "organization_id":         org_id,
        "service_name":            svc.get("서비스명"),
        "support_type":            svc.get("지원유형"),
        "ai_summary":              svc.get("서비스목적요약"),
        "service_field":           svc.get("서비스분야"),
        "target_users":            svc.get("지원대상"),
        "selection_criteria":      svc.get("선정기준"),
        "support_content":         svc.get("지원내용"),
        "application_method":      svc.get("신청방법"),
        "application_period_text": svc.get("신청기한"),
        "is_always_open":          (svc.get("신청기한") or "").strip() == "상시",
        "required_documents":      svc.get("구비서류"),
        "application_url":         svc.get("온라인신청URL"),
        "detail_url":              svc.get("상세조회URL"),
        "external_site_url":       svc.get("관련사이트"),
        "source_service_id":       svc.get("서비스ID"),
    }
    res = db.table("benefits").insert(row).execute()
    return res.data[0]["id"]

def insert_user_types(db: Client, benefit_id: str, raw: str):
    types = [t.strip() for t in raw.split(",") if t.strip()]
    if not types:
        return
    db.table("benefit_user_types").insert(
        [{"benefit_id": benefit_id, "user_type": t} for t in types]
    ).execute()

def insert_chunks(
    db: Client,
    benefit_id: str,
    chunks: dict[str, str],
    emb_map: dict[str, list[float]],
):
    rows = [
        {
            "benefit_id": benefit_id,
            "chunk_type": ctype,
            "chunk_text": ctext,
            "embedding":  emb_map[ctype],
        }
        for ctype, ctext in chunks.items()
        if ctext and ctype in emb_map
    ]
    if rows:
        db.table("benefit_chunks").insert(rows).execute()


# ── 5. 메인 파이프라인 ────────────────────────────────────────────────────────
async def run():
    db     = create_client(SUPABASE_URL, SUPABASE_KEY)
    openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

    # ── Step 1: API 호출 ──────────────────────────────────────────────────────
    services = await fetch_youth_services()

    # ── Step 2: 중복 필터 ─────────────────────────────────────────────────────
    new_svcs = [s for s in services if not already_imported(db, s.get("서비스ID", ""))]
    skip_cnt = len(services) - len(new_svcs)
    log.info(f"신규: {len(new_svcs)}건  |  중복 skip: {skip_cnt}건")

    if not new_svcs:
        log.info("모두 이미 적재된 데이터입니다. 종료합니다.")
        return

    # ── Step 3: 청크 텍스트 사전 생성 ────────────────────────────────────────
    # flat_chunks: [(svc_idx, chunk_type, chunk_text), ...]
    svc_chunk_map: list[dict[str, str]] = []
    flat_chunks:   list[tuple[int, str, str]] = []

    for svc_idx, svc in enumerate(new_svcs):
        user_types = svc.get("사용자구분", "")
        chunks = build_chunks(svc, user_types)
        svc_chunk_map.append(chunks)
        for ctype, ctext in chunks.items():
            if ctext:
                flat_chunks.append((svc_idx, ctype, ctext))

    log.info(f"총 {len(flat_chunks)}개 청크 생성 ({len(new_svcs)}개 서비스 × 최대 4)")

    # ── Step 4: 임베딩 배치 생성 ──────────────────────────────────────────────
    log.info("임베딩 생성 시작...")
    texts      = [fc[2] for fc in flat_chunks]
    embeddings = await embed_texts(openai, texts)

    # svc_idx → {chunk_type: embedding} 매핑
    emb_by_svc: dict[int, dict[str, list[float]]] = defaultdict(dict)
    for i, (svc_idx, ctype, _) in enumerate(flat_chunks):
        emb_by_svc[svc_idx][ctype] = embeddings[i]

    log.info("임베딩 생성 완료")

    # ── Step 5: DB 삽입 ───────────────────────────────────────────────────────
    log.info("DB 삽입 시작...")
    ok, fail = 0, 0

    for svc_idx, svc in enumerate(new_svcs):
        name = svc.get("서비스명", "(이름없음)")
        try:
            org_id     = get_or_create_org(db, svc.get("소관기관명", "미상"), svc.get("전화문의"))
            benefit_id = insert_benefit(db, svc, org_id)
            insert_user_types(db, benefit_id, svc.get("사용자구분", ""))
            insert_chunks(db, benefit_id, svc_chunk_map[svc_idx], emb_by_svc[svc_idx])
            log.info(f"  [{ok+1}/{len(new_svcs)}] ✓ {name}")
            ok += 1
        except Exception as e:
            log.error(f"  [{ok+fail+1}/{len(new_svcs)}] ✗ {name} — {e}")
            fail += 1

    # ── 완료 요약 ─────────────────────────────────────────────────────────────
    total_chunks = sum(
        len([c for c in svc_chunk_map[i].values() if c])
        for i in range(ok)
    )
    print()
    log.info("=" * 50)
    log.info(f"완료  성공: {ok}건  실패: {fail}건  skip: {skip_cnt}건")
    log.info(f"benefit_chunks 삽입: 약 {total_chunks}행")
    log.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(run())
