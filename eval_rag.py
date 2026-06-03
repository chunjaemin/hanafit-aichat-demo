"""
RAG 검색 품질 평가 스크립트
실행: python eval_rag.py
서버가 http://localhost:8000 에서 실행 중이어야 합니다.
"""
import json
import asyncio
import httpx
from pathlib import Path

API_URL = "http://localhost:8000/api/v1/rag/search"
TEST_CASES_PATH = Path(__file__).parent / "eval_test_cases.json"
TOP_K = 5
THRESHOLD = 0.1  # 여기서 threshold 조정


async def search(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(
            API_URL,
            json={"query": query, "top_k": TOP_K, "threshold": THRESHOLD},
        )
        res.raise_for_status()
        return res.json()["chunks"]


def hit_at_k(chunks: list[dict], expected_keyword: str, k: int) -> bool:
    return any(expected_keyword in c["service_name"] for c in chunks[:k])


async def evaluate():
    test_cases = json.loads(TEST_CASES_PATH.read_text(encoding="utf-8"))

    print(f"\n{'='*60}")
    print(f"RAG 평가 — {len(test_cases)}개 테스트 케이스  (top_k={TOP_K})")
    print(f"{'='*60}\n")

    results = []
    for tc in test_cases:
        query = tc["query"]
        expected = tc["expected"]

        try:
            chunks = await search(query)
        except Exception as e:
            print(f"❗ API 오류 [{query}]: {e}\n")
            continue

        h1 = hit_at_k(chunks, expected, 1)
        h3 = hit_at_k(chunks, expected, 3)
        h5 = hit_at_k(chunks, expected, 5)
        top1 = chunks[0]["service_name"] if chunks else "(결과 없음)"
        top1_score = chunks[0]["similarity"] if chunks else 0.0

        results.append({"query": query, "expected": expected, "h1": h1, "h3": h3, "h5": h5})

        if h1:
            icon = "✅"
        elif h3:
            icon = "🔶"
        elif h5:
            icon = "🔸"
        else:
            icon = "❌"

        print(f"{icon} {query}")
        print(f"   예상: {expected}")
        print(f"   Top1: {top1}  (similarity={top1_score:.3f})")
        top5_scores = "  ".join(f"{c['similarity']:.3f}" for c in chunks)
        print(f"   Top{len(chunks)} scores: [{top5_scores}]")
        print(f"   Hit@1={int(h1)} | Hit@3={int(h3)} | Hit@5={int(h5)}\n")

    if not results:
        print("평가 결과 없음.")
        return

    n = len(results)
    hr1 = sum(r["h1"] for r in results) / n
    hr3 = sum(r["h3"] for r in results) / n
    hr5 = sum(r["h5"] for r in results) / n

    print(f"{'='*60}")
    print(f"Hit Rate@1 : {hr1:.0%}  ({sum(r['h1'] for r in results)}/{n})")
    print(f"Hit Rate@3 : {hr3:.0%}  ({sum(r['h3'] for r in results)}/{n})")
    print(f"Hit Rate@5 : {hr5:.0%}  ({sum(r['h5'] for r in results)}/{n})")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(evaluate())
