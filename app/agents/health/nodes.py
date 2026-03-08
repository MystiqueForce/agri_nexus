"""
Health Agent — Pipeline Nodes
------------------------------
Individual LangGraph nodes implementing the full health diagnosis pipeline:
translate → analyze_multimodal → extract_symptoms → classify_domain →
diagnose → check_confidence → estimate_severity → retrieve_knowledge →
generate_treatment → generate_explanation → translate_response
"""

import json
from app.agents.health.state import HealthState
from app.services import bedrock_service, translate_service, knowledge_base_service
from app.config import CONFIDENCE_THRESHOLD


# ═══════════════════════════════════════════════════════════════
# Node 1: Translate Input
# ═══════════════════════════════════════════════════════════════

def translate_input(state: HealthState) -> dict:
    """Detect language and translate query to English."""
    query = state["query"]
    try:
        lang = translate_service.detect_language(query)
        english_query = translate_service.translate_to_english(query, lang)
    except Exception:
        lang = "en"
        english_query = query

    # If there's a follow-up answer, translate that too
    follow_up = state.get("follow_up_answer")
    if follow_up:
        try:
            follow_up = translate_service.translate_to_english(follow_up, lang)
        except Exception:
            pass
        english_query = f"{english_query}\n\nAdditional info from farmer: {follow_up}"

    return {"original_language": lang, "english_query": english_query}


# ═══════════════════════════════════════════════════════════════
# Node 2: Analyze Multimodal Input (VLM)
# ═══════════════════════════════════════════════════════════════

def analyze_multimodal(state: HealthState) -> dict:
    """If image or video is present, use VLM to analyze it."""
    image_data = state.get("image_data")
    video_data = state.get("video_data")
    english_query = state.get("english_query", "")

    if not image_data and not video_data:
        return {"visual_analysis": ""}

    vlm_prompt = (
        "You are an agricultural and veterinary expert. "
        "Analyze this image/video carefully and describe:\n"
        "1. What you observe (plant/animal condition, visible symptoms)\n"
        "2. Any signs of disease, pest damage, or deficiency\n"
        "3. The health condition of what you see\n\n"
        f"Farmer's description: {english_query}"
    )

    system_prompt = (
        "You are an expert agricultural scientist and veterinarian. "
        "Provide detailed, accurate visual analysis for crop and livestock health diagnosis."
    )

    try:
        if image_data:
            media_type = state.get("image_media_type", "image/jpeg")
            analysis = bedrock_service.invoke_model_with_image(
                vlm_prompt, image_data, media_type, system_prompt
            )
        elif video_data:
            media_type = state.get("video_media_type", "video/mp4")
            analysis = bedrock_service.invoke_model_with_video(
                vlm_prompt, video_data, media_type, system_prompt
            )
        else:
            analysis = ""
    except Exception as e:
        analysis = f"Visual analysis unavailable: {str(e)}"

    return {"visual_analysis": analysis}


# ═══════════════════════════════════════════════════════════════
# Node 3: Extract Symptoms
# ═══════════════════════════════════════════════════════════════

def extract_symptoms(state: HealthState) -> dict:
    """Extract structured symptoms from the query + visual analysis."""
    english_query = state.get("english_query", "")
    visual = state.get("visual_analysis", "")

    combined = english_query
    if visual:
        combined += f"\n\nVisual analysis findings: {visual}"

    prompt = f"""You are an agricultural and veterinary symptom extraction expert.

From the following farmer's description, extract:
1. A list of symptoms
2. The entity affected (e.g., "tomato", "cow", "wheat", "chicken")

Farmer's input:
{combined}

Respond in strict JSON format:
{{
  "symptoms": ["symptom1", "symptom2", ...],
  "entity": "entity name"
}}"""

    try:
        result = bedrock_service.invoke_model_json(prompt)
        return {
            "symptoms": result.get("symptoms", []),
            "entity": result.get("entity", "unknown"),
        }
    except Exception:
        return {"symptoms": [english_query], "entity": "unknown"}


# ═══════════════════════════════════════════════════════════════
# Node 4: Classify Domain
# ═══════════════════════════════════════════════════════════════

def classify_domain(state: HealthState) -> dict:
    """Classify whether the issue is plant-related or livestock-related."""
    entity = state.get("entity", "unknown")
    symptoms = state.get("symptoms", [])

    prompt = f"""Classify the following agricultural health query into one of two domains:
- "plant" (crops, fruits, vegetables, trees, leaves, soil)
- "livestock" (animals, cattle, poultry, goats, sheep, fish)

Entity: {entity}
Symptoms: {', '.join(symptoms)}

Respond with ONLY the word "plant" or "livestock"."""

    try:
        result = bedrock_service.invoke_model(prompt).strip().lower()
        domain = "plant" if "plant" in result else "livestock"
    except Exception:
        domain = "plant"

    return {"domain": domain}


# ═══════════════════════════════════════════════════════════════
# Node 5: Diagnose
# ═══════════════════════════════════════════════════════════════

def diagnose(state: HealthState) -> dict:
    """Infer possible diseases with confidence scores."""
    entity = state.get("entity", "unknown")
    symptoms = state.get("symptoms", [])
    domain = state.get("domain", "plant")
    visual = state.get("visual_analysis", "")

    domain_context = (
        "crop diseases, pest infestations, nutrient deficiencies, and plant pathology"
        if domain == "plant"
        else "livestock diseases, parasites, infections, and animal welfare issues"
    )

    prompt = f"""You are an expert in {domain_context}.

Entity: {entity}
Symptoms: {', '.join(symptoms)}
{"Visual analysis: " + visual if visual else ""}

Based on these symptoms, provide your top 3 most likely diagnoses with confidence scores (0.0 to 1.0).
The confidence scores must sum to no more than 1.0.

Respond in strict JSON format:
{{
  "diseases": [
    {{"disease": "Disease Name 1", "confidence": 0.XX}},
    {{"disease": "Disease Name 2", "confidence": 0.XX}},
    {{"disease": "Disease Name 3", "confidence": 0.XX}}
  ]
}}"""

    try:
        result = bedrock_service.invoke_model_json(prompt)
        diseases = result.get("diseases", [])
        if diseases:
            top = max(diseases, key=lambda d: d.get("confidence", 0))
            return {
                "diseases": diseases,
                "top_diagnosis": top["disease"],
                "top_confidence": top["confidence"],
            }
    except Exception:
        pass

    return {
        "diseases": [{"disease": "Unknown condition", "confidence": 0.3}],
        "top_diagnosis": "Unknown condition",
        "top_confidence": 0.3,
    }


# ═══════════════════════════════════════════════════════════════
# Node 6: Check Confidence
# ═══════════════════════════════════════════════════════════════

def check_confidence(state: HealthState) -> dict:
    """
    Decide whether to proceed with diagnosis or ask for more info.

    NEVER asks follow-up if:
    - The user already provided a follow-up answer (prevents loops)
    - Confidence is above threshold
    - There are >= 3 symptoms (enough context to diagnose)
    - An image or video was provided (visual analysis supplements text)
    """
    confidence = state.get("top_confidence", 0)
    follow_up_answer = state.get("follow_up_answer")
    symptoms = state.get("symptoms", [])
    visual = state.get("visual_analysis", "")
    image_data = state.get("image_data")
    video_data = state.get("video_data")

    # ── Skip follow-up in these cases (proceed with diagnosis) ──
    # 1. User already gave a follow-up answer → never ask again
    if follow_up_answer:
        return {"needs_follow_up": False, "follow_up_question": ""}

    # 2. Confidence is above the threshold
    if confidence >= CONFIDENCE_THRESHOLD:
        return {"needs_follow_up": False, "follow_up_question": ""}

    # 3. Enough symptoms to work with (3 or more)
    if len(symptoms) >= 3:
        return {"needs_follow_up": False, "follow_up_question": ""}

    # 4. Visual analysis was done (image/video provides extra context)
    if image_data or video_data or (visual and "unavailable" not in visual.lower()):
        return {"needs_follow_up": False, "follow_up_question": ""}

    # ── Only ask follow-up for genuinely vague, text-only queries ──
    entity = state.get("entity", "")
    diseases = state.get("diseases", [])

    disease_names = [d["disease"] for d in diseases[:3]]

    prompt = f"""You are diagnosing a {state.get('domain', 'plant')} health issue.

Entity: {entity}
Symptoms so far: {', '.join(symptoms)}
Possible diagnoses: {', '.join(disease_names)}

The confidence is low ({confidence:.0%}). Generate ONE specific follow-up question
to help narrow down the diagnosis. Make it simple and farmer-friendly.

Respond with ONLY the question, nothing else."""

    try:
        question = bedrock_service.invoke_model(prompt).strip()
    except Exception:
        question = "Can you provide more details about the symptoms?"

    return {"needs_follow_up": True, "follow_up_question": question}


# ═══════════════════════════════════════════════════════════════
# Node 7: Estimate Severity
# ═══════════════════════════════════════════════════════════════

def estimate_severity(state: HealthState) -> dict:
    """Calculate severity score and triage level."""
    entity = state.get("entity", "")
    symptoms = state.get("symptoms", [])
    diagnosis = state.get("top_diagnosis", "")
    domain = state.get("domain", "plant")
    visual = state.get("visual_analysis", "")

    prompt = f"""You are an agricultural health severity assessment expert.

Domain: {domain}
Entity: {entity}
Diagnosis: {diagnosis}
Symptoms: {', '.join(symptoms)}
{"Visual observations: " + visual if visual else ""}

Assess the severity considering:
- Symptom intensity and spread
- Disease aggressiveness
- Potential for crop/livestock loss
- Urgency of intervention needed

Respond in strict JSON format:
{{
  "severity": "Low" | "Moderate" | "High" | "Critical",
  "severity_score": 0.0 to 1.0,
  "triage_level": "Monitor" | "Treat Soon" | "Treat Immediately" | "Emergency"
}}"""

    try:
        result = bedrock_service.invoke_model_json(prompt)
        return {
            "severity": result.get("severity", "Moderate"),
            "severity_score": result.get("severity_score", 0.5),
            "triage_level": result.get("triage_level", "Treat Soon"),
        }
    except Exception:
        return {
            "severity": "Moderate",
            "severity_score": 0.5,
            "triage_level": "Treat Soon",
        }


# ═══════════════════════════════════════════════════════════════
# Node 8: Retrieve Knowledge
# ═══════════════════════════════════════════════════════════════

def retrieve_knowledge(state: HealthState) -> dict:
    """Retrieve treatment protocols from the Bedrock Knowledge Base (RAG)."""
    diagnosis = state.get("top_diagnosis", "")
    entity = state.get("entity", "")
    domain = state.get("domain", "plant")

    query = f"{diagnosis} treatment protocol for {entity} {domain}"

    try:
        context = knowledge_base_service.retrieve_and_format(query, top_k=5)
    except Exception:
        context = ""

    return {"knowledge_context": context}


# ═══════════════════════════════════════════════════════════════
# Node 9: Generate Treatment Plan
# ═══════════════════════════════════════════════════════════════

def generate_treatment(state: HealthState) -> dict:
    """Generate a detailed treatment plan using diagnosis + KB context."""
    diagnosis = state.get("top_diagnosis", "")
    entity = state.get("entity", "")
    domain = state.get("domain", "plant")
    severity = state.get("severity", "Moderate")
    kb_context = state.get("knowledge_context", "")

    context_section = ""
    if kb_context:
        context_section = f"""

Reference knowledge base information:
{kb_context}
"""

    prompt = f"""You are an expert {domain} health advisor for farmers.

Diagnosis: {diagnosis}
Entity: {entity}
Severity: {severity}
{context_section}

Generate a practical, farmer-friendly treatment plan including:
1. Immediate actions to take
2. Specific treatments (medicines, fungicides, pesticides with dosages)
3. Prevention tips for the future
4. When to seek professional veterinary/agricultural help

{"If the knowledge base information is insufficient, use your expert knowledge to supplement." if not kb_context else "Use the knowledge base information as primary source, supplement with your expertise if needed."}

Keep the language simple and actionable for a farmer."""

    try:
        plan = bedrock_service.invoke_model(prompt)
    except Exception:
        plan = "Please consult a local agricultural officer or veterinarian for treatment advice."

    return {"treatment_plan": plan}


# ═══════════════════════════════════════════════════════════════
# Node 10: Generate Explanation (Explainable AI)
# ═══════════════════════════════════════════════════════════════

def generate_explanation(state: HealthState) -> dict:
    """Generate an explainable AI output with reasoning chain."""
    diagnosis = state.get("top_diagnosis", "")
    diseases = state.get("diseases", [])
    symptoms = state.get("symptoms", [])
    entity = state.get("entity", "")
    severity = state.get("severity", "Moderate")
    severity_score = state.get("severity_score", 0.5)
    triage_level = state.get("triage_level", "Treat Soon")
    treatment = state.get("treatment_plan", "")
    visual = state.get("visual_analysis", "")
    confidence = state.get("top_confidence", 0)

    # Build structured explanation
    reasoning_points = []
    for s in symptoms:
        reasoning_points.append(f"• {s} detected")
    if visual:
        reasoning_points.append("• Visual analysis confirms observations")

    disease_list = "\n".join(
        [f"  - {d['disease']}: {d['confidence']:.0%}" for d in diseases]
    )

    explanation = f"""Diagnosis: {diagnosis}

Reasoning:
{chr(10).join(reasoning_points)}

Possible Conditions:
{disease_list}

Severity: {severity} (Score: {severity_score:.2f})
Triage: {triage_level}

Recommendation:
{treatment}"""

    return {"explanation": explanation, "final_response": explanation}


# ═══════════════════════════════════════════════════════════════
# Node 11: Translate Response
# ═══════════════════════════════════════════════════════════════

def translate_response(state: HealthState) -> dict:
    """Translate the final response back to the farmer's original language."""
    lang = state.get("original_language", "en")
    response = state.get("final_response", "")

    if lang == "en" or not response:
        return {"final_response": response}

    try:
        translated = translate_service.translate_from_english(response, lang)
        return {"final_response": translated}
    except Exception:
        return {"final_response": response}


# ═══════════════════════════════════════════════════════════════
# Follow-up Response Node
# ═══════════════════════════════════════════════════════════════

def prepare_follow_up_response(state: HealthState) -> dict:
    """Prepare the follow-up question response when confidence is low."""
    question = state.get("follow_up_question", "")
    lang = state.get("original_language", "en")

    if lang != "en":
        try:
            question = translate_service.translate_from_english(question, lang)
        except Exception:
            pass

    return {"final_response": question}
