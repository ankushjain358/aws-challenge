import json
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2, event_source
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

@event_source(data_class=APIGatewayProxyEventV2)
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext) -> Dict[str, Any]:
    """
    Delete a VPC and its metadata using the VPC ID from the request URL.
    """
    try:
        # 1. Validation - Read the VPC ID from the /vpcs/{vpc_id} URL path parameter.
        path_parameters = event.path_parameters or {}
        vpc_id = path_parameters.get("vpc_id")
        if not vpc_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing required path parameter: vpc_id."}),
            }

        # 2. Create clients
        ec2 = boto3.client("ec2")
        table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

        # 3. Validation - If the ID doesn’t exist, the describe_vpcs will throw a ClientError
        ec2.describe_vpcs(VpcIds=[vpc_id])

        # 4. Delete the VPC
        ec2.delete_vpc(VpcId=vpc_id)
        
        # 5. Update the DynamoDB
        table.delete_item(Key={"id": vpc_id})

        logger.info("VPC deleted", extra={"vpc_id": vpc_id})
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "VPC deleted successfully.", "vpc_id": vpc_id}),
        }
    except Exception:
        logger.exception("Failed to delete VPC")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error."}),
        }