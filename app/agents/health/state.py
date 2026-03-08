"""
Health Agent — State Definition
---------------------------------
TypedDict defining the state that flows through the Health Agent LangGraph pipeline.
"""

from typing import TypedDict, Optional, Any


class HealthState(TypedDict, total=False):
    # ── Input ────────────────────────────────────
    query: str
    farm_id: str
    image_data: Optional[bytes]
    image_media_type: Optional[str]
    video_data: Optional[bytes]
    video_media_type: Optional[str]
    follow_up_answer: Optional[str]
    session_id: Optional[str]

    # ── Language ─────────────────────────────────
    original_language: str
    english_query: str

    # ── Multimodal Analysis ──────────────────────
    visual_analysis: str

    # ── Symptom Extraction ───────────────────────
    symptoms: list[str]
    entity: str

    # ── Classification ───────────────────────────
    domain: str  # "plant" or "livestock"

    # ── Diagnosis ────────────────────────────────
    diseases: list[dict]  # [{disease, confidence}, ...]
    top_diagnosis: str
    top_confidence: float

    # ── Follow-up ────────────────────────────────
    needs_follow_up: bool
    follow_up_question: str

    # ── Severity ─────────────────────────────────
    severity: str  # "Low", "Moderate", "High", "Critical"
    severity_score: float
    triage_level: str

    # ── Knowledge Retrieval ──────────────────────
    knowledge_context: str

    # ── Treatment & Explanation ──────────────────
    treatment_plan: str
    explanation: str

    # ── Final Output ─────────────────────────────
    final_response: str

    # ── Error Handling ───────────────────────────
    error: Optional[str]
