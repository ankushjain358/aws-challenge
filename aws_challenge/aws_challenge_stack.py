from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
)
import aws_cdk as cdk
from constructs import Construct

class AwsChallengeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # 1.1. Create a Cognito User Pool with minimal configuration
        userpool = cognito.UserPool(self, "aws-challenge-user-pool",
            user_pool_name="aws-challenge-user-pool",
            self_sign_up_enabled=True,
            # sign_in_aliases=cognito.SignInAliases(email=True, username=False, phone=False, preferred_username=False),
            # account_recovery=cognito.AccountRecovery.EMAIL_ONLY
        )

        # 1.2. Create an app client for the user pool with client credentials flow enabled
        # Note:Keeping client credentials flow for now for the simplicity of the challenge
        # Else we would need to create users in pool, and then have to generate tokens for them to test the API, which is not the focus of this challenge
        app_client = userpool.add_client("aws-challenge-app-client",
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    client_credentials=True,
                ),
                # scopes=[cognito.OAuthScope.custom("aws-challenge-scope")],
            )
        )

        # 2. Create a DynamoDB table with a primary key of "id" (string) and a sort key of "timestamp" (number)
        dynamodb_table = dynamodb.Table(self, "aws-challenge-table",
            table_name="aws-challenge-table",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.NUMBER),
            removal_policy=cdk.RemovalPolicy.DESTROY,  # NOT recommended for production
        )


        # 3. Create an API Gateway REST API with a single resource and method that is protected by the Cognito User Pool authorizer
        api = apigateway.RestApi(self, "aws-challenge-api",
            rest_api_name="aws-challenge-api",
            description="This is the AWS Challenge API"
        )

        ## Output the API URL and Cognito User Pool ID for testing
        cdk.CfnOutput(self, "ApiUrl", value=api.url)
        cdk.CfnOutput(self, "UserPoolId", value=userpool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientId", value=app_client.user_pool_client_id)
        cdk.CfnOutput(self, "DynamoDBTableName", value=dynamodb_table.table_name)

                      

       

## TODO
# 0. Manually create API gateway
# 1. Lambda functions
# 2. IAM roles for lambda functions
# 3. Pylint 
# 4. Documentation        