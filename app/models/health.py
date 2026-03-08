"""
Health Models — Pydantic Schemas
---------------------------------
Request and response schemas for the Health Agent API.
"""

from pydantic import BaseModel, Field
from typing import Optional


class DiagnoseRequest(BaseModel):
    """Request body for health diagnosis."""
    query: str = Field(..., description="Text description of the health issue")
    farm_id: str = Field(default="anonymous", description="Farm identifier")
    follow_up_answer: Optional[str] = Field(
        None, description="Answer to a follow-up question from previous round"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID for multi-turn follow-up conversations"
    )


class SymptomInfo(BaseModel):
    symptoms: list[str]
    entity: str
    domain: str  # "plant" or "livestock"


class DiseaseCandidate(BaseModel):
    disease: str
    confidence: float


class DiagnoseResponse(BaseModel):
    """Full diagnosis response."""
    diagnosis: str = ""
    diseases: list[DiseaseCandidate] = []
    reasoning: str = ""
    severity: str = ""
    severity_score: float = 0.0
    triage_level: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    follow_up_question: Optional[str] = None
    needs_follow_up: bool = False
    session_id: Optional[str] = None
    original_language: str = "en"
