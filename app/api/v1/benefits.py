from fastapi import APIRouter
from app.schemas.benefit import EligibilityRequest, EligibilityResponse

router = APIRouter()


@router.post("/eligibility", response_model=EligibilityResponse)
async def check_eligibility(request: EligibilityRequest) -> EligibilityResponse:
    # 대상자 체크 구현 예정
    return EligibilityResponse(
        eligible=False,
        reason="대상자 체크 기능 준비 중이에요.",
        estimated_amount=None,
    )
