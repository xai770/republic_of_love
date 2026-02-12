"""
Mira router — Pydantic models.
"""
from pydantic import BaseModel
from typing import Optional, List


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    message: str
    uses_du: Optional[bool] = None  # None = unknown, True = du, False = Sie
    history: Optional[List[ChatMessage]] = None  # Conversation history


class GreetingResponse(BaseModel):
    greeting: str
    is_new_yogi: bool
    has_profile: bool
    has_skills: bool
    has_matches: int
    suggested_actions: List[str]
    uses_du: bool  # Server's guess, client can override


class ChatResponse(BaseModel):
    reply: str
    fallback: bool = False  # True if we couldn't answer and logged to mira_questions
    confidence: Optional[str] = None  # 'high', 'medium', 'low' for debugging
    faq_id: Optional[str] = None  # Which FAQ was matched
    language: Optional[str] = None  # 'de' or 'en' — current response language
    actions: Optional[dict] = None  # Structured actions for frontend (e.g. set_filters)


class TourStep(BaseModel):
    step_id: str
    title: str
    message: str
    target: Optional[str] = None  # CSS selector or element ID to highlight
    action: Optional[str] = None  # 'click', 'type', 'scroll'


class TourResponse(BaseModel):
    steps: List[TourStep]
    total_steps: int


class YogiContext(BaseModel):
    has_profile: bool
    skills: List[str]
    match_count: int
    recent_matches: List[dict]
    journey_states: dict


class ProactiveMessage(BaseModel):
    message_type: str  # new_matches, saved_job_open, application_viewed
    message: str
    data: Optional[dict] = None


class ProactiveResponse(BaseModel):
    messages: List[ProactiveMessage]


class ConsentPromptResponse(BaseModel):
    should_prompt: bool
    message: Optional[str] = None
    consent_given: bool = False


class ConsentSubmission(BaseModel):
    email: str
    grant_consent: bool = True
