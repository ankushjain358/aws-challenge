from dataclasses import dataclass
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from mypy_boto3_ec2 import EC2Client
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2, event_source
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


@dataclass
class VpcCreateDTO:
    """Required request fields for creating a VPC."""

    vpc_name: str
    cidr_block: str


def validate_input(payload: Any) -> VpcCreateDTO:
    """Check required request fields and build the VPC creation DTO."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
   
    input_request =  VpcCreateDTO(**payload)

    if not input_request.vpc_name.strip():
        raise ValueError("The 'vpc_name' field cannot be empty.")

    if not input_request.cidr_block.strip():
        raise ValueError("The 'cidr_block' field cannot be empty.")

    return input_request


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Build an API Gateway proxy response with a JSON body."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
    

@event_source(data_class=APIGatewayProxyEventV2)
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext) -> Dict[str, Any]:
    """
    Create a VPC from the request body and store its metadata in DynamoDB.
    """
    try:
        # 1. Parse the API Gateway request body.
        request_body = event.body
        payload = json.loads(request_body) if request_body else None
        vpc_input = validate_input(payload)

        # 2 Create clients
        ec2: EC2Client = boto3.client("ec2") 
        table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

        # 3. Create VPC
        create_result = ec2.create_vpc(
            CidrBlock=vpc_input.cidr_block,
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": [{"Key": "Name", "Value": vpc_input.vpc_name}],
                }
            ],
        )
        vpc = create_result["Vpc"]
        vpc_id = vpc["VpcId"]
        created_at = datetime.now(timezone.utc)
        timestamp = created_at.strftime("%B %d, %Y at %I:%M:%S %p UTC")

        # 4. Store in DynamoDB
        table.put_item(
            Item={
                "id": vpc_id,
                "name": vpc_input.vpc_name,
                "cidr": vpc_input.cidr_block,
                "created_on": timestamp,
            }
        )

        logger.info("VPC created and stored", extra={"vpc_id": vpc_id})

        # 5. Return the response
        return _response(
            200,
            {
                "message": "VPC created successfully.",
                "vpc_id": vpc_id,
                "name": vpc_input.vpc_name,
                "cidr": vpc_input.cidr_block,
                "created_on": timestamp,
            },
        )
    except (ValueError) as error:
        logger.info("Invalid VPC creation request", extra={"error": str(error)})
        return _response(400, {"error": str(error)})
    except Exception:
        logger.exception("Failed to create or store VPC")
        return _response(500, {"error": "Internal server error."})