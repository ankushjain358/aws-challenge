import json
from typing import Any, Dict
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEventV2, event_source
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

@event_source(data_class=APIGatewayProxyEventV2)
def lambda_handler(event: APIGatewayProxyEventV2, context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda function to perform a health check.
    """
    logger.info("Health check invoked.")
    
    response: Dict[str, Any] = {
        "statusCode": 200,
        "body": json.dumps({"message": "Service is healthy!"})
    }
    
    return response