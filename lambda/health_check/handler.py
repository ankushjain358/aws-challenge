import json
import logging
from typing import Any, Dict

# Set up logging best practices
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to perform a health check.
    """
    logger.info("Health check invoked.")
    
    response: Dict[str, Any] = {
        "statusCode": 200,
        "body": json.dumps({"message": "Service is healthy!"})
    }
    
    return response