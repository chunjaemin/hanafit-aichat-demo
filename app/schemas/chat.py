from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class UserProfile(BaseModel):
    age: Optional[int] = None
    income_percentile: Optional[int] = None
    region: Optional[str] = None
    employment_status: Optional[str] = None


class ChatProcessRequest(BaseModel):
    message: str
    chat_history: list[ChatMessage] = []
    user_profile: Optional[UserProfile] = None


class Citation(BaseModel):
    source: str
    snippet: str


class BenefitCard(BaseModel):
    id: str
    title: str
    summary: str
    amount: str
    target: str
    deadline: Optional[str] = None
    link: Optional[str] = None


class ExtractedUserInfo(BaseModel):
    age: Optional[int] = None
    region: Optional[str] = None


class ChatProcessResponse(BaseModel):
    intent: str
    text: str
    benefit_cards: Optional[list[BenefitCard]] = None
    suggested_questions: list[str]
    citations: Optional[list[Citation]] = None
    extracted_user_info: Optional[ExtractedUserInfo] = None
