"""
AWS Translate Service
---------------------
Language detection and translation using AWS Translate.
Supports all major Indian languages.
"""

import boto3
from app.config import AWS_REGION

_client = boto3.client("translate", region_name=AWS_REGION)


def detect_language(text: str) -> str:
    """
    Detect the dominant language of the input text.
    Returns the language code (e.g., 'hi', 'en', 'ta').
    """
    # Use Comprehend for more accurate detection
    comprehend = boto3.client("comprehend", region_name=AWS_REGION)
    response = comprehend.detect_dominant_language(Text=text[:500])
    languages = response.get("Languages", [])
    if languages:
        return languages[0]["LanguageCode"]
    return "en"


def translate_to_english(text: str, source_lang: str) -> str:
    """Translate text from source language to English."""
    if source_lang == "en":
        return text
    response = _client.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode="en",
    )
    return response["TranslatedText"]


def translate_from_english(text: str, target_lang: str) -> str:
    """Translate text from English to target language."""
    if target_lang == "en":
        return text
    response = _client.translate_text(
        Text=text,
        SourceLanguageCode="en",
        TargetLanguageCode=target_lang,
    )
    return response["TranslatedText"]
