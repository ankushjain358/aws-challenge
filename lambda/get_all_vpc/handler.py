import json
import os
from typing import Any, Dict

import boto3
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2, event_source
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

@event_source(data_class=APIGatewayProxyEventV2)
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext) -> Dict[str, Any]:
    """
    Return all VPC metadata records stored in DynamoDB.
    """
    try:
        # 1. Create client
        table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

        # 2. Scan table
        scan_result = table.scan()
        items = scan_result.get("Items", [])
        while "LastEvaluatedKey" in scan_result:
            scan_result = table.scan(
                ExclusiveStartKey=scan_result["LastEvaluatedKey"]
            )
            items.extend(scan_result.get("Items", []))

        # 3. Return response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"items": items}),
        }
    except Exception:
        logger.exception("Failed to scan VPC metadata")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error."}),
        }