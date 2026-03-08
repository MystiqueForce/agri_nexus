import boto3
import json

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1"   # or ap-south-1 if available
)

response = client.converse(
    modelId="qwen.qwen3-vl-235b-a22b",
    messages=[
        {
            "role": "user",
            "content": [
                {"text": "Act like Shakespeare and write a poem about Generative AI"}
            ]
        }
    ],
    inferenceConfig={
        "maxTokens": 512,
        "temperature": 0.7,
        "topP": 0.9
    }
)

print(response["output"]["message"]["content"][0]["text"])