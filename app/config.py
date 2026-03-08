"""
NexusAgri Configuration
-----------------------
Central configuration for AWS services, model paths, and application settings.
"""

import os
from pathlib import Path

# ── Project Paths ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data"
DATASETS_DIR = BASE_DIR / "datasets"

# ── AWS Configuration ─────────────────────────────────────────
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Bedrock
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "qwen.qwen3-vl-235b-a22b")
BEDROCK_KNOWLEDGE_BASE_ID = os.getenv("BEDROCK_KB_ID", "YVWBJK3ABN")

# DynamoDB
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "NexusAgriFarms")

# ── Model Files ───────────────────────────────────────────────
PRICE_MODEL_PATH = MODELS_DIR / "price_model.pkl"
ARRIVAL_MODEL_PATH = MODELS_DIR / "arrival_model.pkl"
MARKET_ENCODER_PATH = MODELS_DIR / "market_encoder.pkl"
CROP_ENCODER_PATH = MODELS_DIR / "crop_encoder.pkl"

# ── Data Files ────────────────────────────────────────────────
MANDIS_CSV_PATH = BASE_DIR / "mandis.csv"
FEATURES_DATASET_PATH = BASE_DIR / "features_dataset.csv"

# ── Agent Settings ────────────────────────────────────────────
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
MAX_FOLLOW_UP_ROUNDS = int(os.getenv("MAX_FOLLOW_UP_ROUNDS", "2"))

# ── Bedrock Inference Settings ────────────────────────────────
BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "2048"))
BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.3"))
BEDROCK_TOP_P = float(os.getenv("BEDROCK_TOP_P", "0.9"))

# ── Weather API ───────────────────────────────────────────────
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# ── Supported Languages ──────────────────────────────────────
# AWS Translate language codes for Indian languages
SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "or": "Odia",
    "as": "Assamese",
    "en": "English",
}
