"""
Farm Memory — DynamoDB Layer
-----------------------------
CRUD operations for per-farm persistent context.
Stores crops, livestock, harvest dates, treatment history, and past recommendations.
"""

import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
from app.config import AWS_REGION, DYNAMODB_TABLE_NAME

_dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)


def _get_table():
    """Get or create the DynamoDB table."""
    table = _dynamodb.Table(DYNAMODB_TABLE_NAME)
    try:
        table.load()
    except Exception:
        # Create table if it doesn't exist
        table = _dynamodb.create_table(
            TableName=DYNAMODB_TABLE_NAME,
            KeySchema=[
                {"AttributeName": "farm_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "farm_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
    return table


def get_farm(farm_id: str) -> dict | None:
    """Retrieve a farm profile by farm_id."""
    table = _get_table()
    response = table.get_item(Key={"farm_id": farm_id})
    return response.get("Item")


def update_farm(farm_id: str, data: dict) -> dict:
    """
    Upsert farm data. Merges provided fields into the existing record.
    """
    table = _get_table()

    # Build update expression dynamically
    update_parts = []
    expr_names = {}
    expr_values = {}

    for key, value in data.items():
        if key == "farm_id":
            continue
        safe_key = f"#{key}"
        safe_val = f":{key}"
        update_parts.append(f"{safe_key} = {safe_val}")
        expr_names[safe_key] = key
        expr_values[safe_val] = value

    if not update_parts:
        return get_farm(farm_id)

    # Add last_updated timestamp
    update_parts.append("#updated = :updated")
    expr_names["#updated"] = "last_updated"
    expr_values[":updated"] = datetime.utcnow().isoformat()

    response = table.update_item(
        Key={"farm_id": farm_id},
        UpdateExpression="SET " + ", ".join(update_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes", {})


def add_treatment_history(farm_id: str, record: dict) -> dict:
    """Append a treatment record to the farm's treatment history."""
    table = _get_table()
    record["timestamp"] = datetime.utcnow().isoformat()

    response = table.update_item(
        Key={"farm_id": farm_id},
        UpdateExpression=(
            "SET treatment_history = list_append("
            "if_not_exists(treatment_history, :empty), :record)"
        ),
        ExpressionAttributeValues={
            ":record": [record],
            ":empty": [],
        },
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes", {})


def add_recommendation(farm_id: str, record: dict) -> dict:
    """Append a recommendation to the farm's past recommendations."""
    table = _get_table()
    record["timestamp"] = datetime.utcnow().isoformat()

    response = table.update_item(
        Key={"farm_id": farm_id},
        UpdateExpression=(
            "SET past_recommendations = list_append("
            "if_not_exists(past_recommendations, :empty), :record)"
        ),
        ExpressionAttributeValues={
            ":record": [record],
            ":empty": [],
        },
        ReturnValues="ALL_NEW",
    )
    return response.get("Attributes", {})
