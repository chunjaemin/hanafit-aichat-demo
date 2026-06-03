from pydantic import BaseModel
from typing import Optional


class EligibilityRequest(BaseModel):
    benefit_id: str
    benefit_content: str
    user_profile: dict


class EligibilityResponse(BaseModel):
    eligible: bool
    reason: str
    estimated_amount: Optional[str] = None
