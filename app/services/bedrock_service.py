"""
AWS Bedrock Service
-------------------
Wrapper for Qwen3-VL model calls via AWS Bedrock Converse API.
Supports text-only, image+text, and video+text (multimodal) invocations.
"""

import json
import boto3
from app.config import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    BEDROCK_MAX_TOKENS,
    BEDROCK_TEMPERATURE,
    BEDROCK_TOP_P,
)

_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def invoke_model(prompt: str, system_prompt: str | None = None) -> str:
    """Text-only invocation of the Bedrock model."""
    messages = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        }
    ]
    kwargs = _build_kwargs(messages, system_prompt)
    response = _client.converse(**kwargs)
    return _extract_text(response)


def invoke_model_with_image(
    prompt: str,
    image_bytes: bytes,
    media_type: str = "image/jpeg",
    system_prompt: str | None = None,
) -> str:
    """Multimodal invocation with an image."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": media_type.split("/")[-1],
                        "source": {"bytes": image_bytes},
                    }
                },
                {"text": prompt},
            ],
        }
    ]
    kwargs = _build_kwargs(messages, system_prompt)
    response = _client.converse(**kwargs)
    return _extract_text(response)


def invoke_model_with_video(
    prompt: str,
    video_bytes: bytes,
    media_type: str = "video/mp4",
    system_prompt: str | None = None,
) -> str:
    """Multimodal invocation with a video."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "video": {
                        "format": media_type.split("/")[-1],
                        "source": {"bytes": video_bytes},
                    }
                },
                {"text": prompt},
            ],
        }
    ]
    kwargs = _build_kwargs(messages, system_prompt)
    response = _client.converse(**kwargs)
    return _extract_text(response)


def invoke_model_json(prompt: str, system_prompt: str | None = None) -> dict:
    """Invoke model and parse JSON from the response."""
    raw = invoke_model(prompt, system_prompt)
    # Try to extract JSON from markdown code blocks if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


def invoke_model_with_image_json(
    prompt: str,
    image_bytes: bytes,
    media_type: str = "image/jpeg",
    system_prompt: str | None = None,
) -> dict:
    """Invoke model with image and parse JSON from the response."""
    raw = invoke_model_with_image(prompt, image_bytes, media_type, system_prompt)
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)


# ── Private Helpers ───────────────────────────────────────────

def _build_kwargs(messages: list, system_prompt: str | None) -> dict:
    kwargs = {
        "modelId": BEDROCK_MODEL_ID,
        "messages": messages,
        "inferenceConfig": {
            "maxTokens": BEDROCK_MAX_TOKENS,
            "temperature": BEDROCK_TEMPERATURE,
            "topP": BEDROCK_TOP_P,
        },
    }
    if system_prompt:
        kwargs["system"] = [{"text": system_prompt}]
    return kwargs


def _extract_text(response: dict) -> str:
    return response["output"]["message"]["content"][0]["text"]
