"""
Knowledge Base Service
----------------------
Retrieves relevant passages from AWS Bedrock Knowledge Base for RAG.
"""

import boto3
from app.config import AWS_REGION, BEDROCK_KNOWLEDGE_BASE_ID

_client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve relevant passages from the Bedrock Knowledge Base.

    Returns a list of dicts:
        [{"text": str, "score": float, "source": str}, ...]
    """
    if not BEDROCK_KNOWLEDGE_BASE_ID:
        # If no KB configured, return empty — agent will use VLM fallback
        return []

    response = _client.retrieve(
        knowledgeBaseId=BEDROCK_KNOWLEDGE_BASE_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {
                "numberOfResults": top_k,
            }
        },
    )

    results = []
    for item in response.get("retrievalResults", []):
        content = item.get("content", {}).get("text", "")
        score = item.get("score", 0.0)
        source = (
            item.get("location", {})
            .get("s3Location", {})
            .get("uri", "unknown")
        )
        results.append({
            "text": content,
            "score": score,
            "source": source,
        })

    return results


def retrieve_and_format(query: str, top_k: int = 5) -> str:
    """
    Retrieve from KB and format as a context string for the LLM.
    Falls back to empty string if KB is not configured.
    """
    results = retrieve(query, top_k)
    if not results:
        return ""

    context_parts = []
    for i, r in enumerate(results, 1):
        context_parts.append(f"[Source {i}]: {r['text']}")

    return "\n\n".join(context_parts)
