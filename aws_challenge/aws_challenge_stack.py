from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_lambda,
    aws_iam as iam,
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
            removal_policy=cdk.RemovalPolicy.DESTROY,  # NOT recommended for production
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
        dynamodb_table = dynamodb.Table(self, "aws-challenge-metadata-table",
            table_name="aws-challenge-metadata-table",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.NUMBER),
            removal_policy=cdk.RemovalPolicy.DESTROY,  # NOT recommended for production
        )

        # 3. Lambda functions

        # 3.1 Create a Lambda function to create a VPC and store its metadata in DynamoDB
        create_vpc_lambda = aws_lambda.Function(
            self,
            "aws-challenge-create-vpc-lambda",
            function_name="aws-challenge-create-vpc-lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_14,
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda/create_vpc"),
            environment={
                "TABLE_NAME": dynamodb_table.table_name,
            },
        )

        # 3.2 Create a Lambda function to get the VPC metadata from DynamoDB
        get_all_vpc_lambda = aws_lambda.Function(
            self,
            "aws-challenge-get-all-vpc-lambda",
            function_name="aws-challenge-get-all-vpc-lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_14,
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda/get_vpc"),
            environment={
                "TABLE_NAME": dynamodb_table.table_name,
            },
        )

        # 3.3 Create a lambda function to delete a VPC and its metadata from DynamoDB
        delete_vpc_lambda = aws_lambda.Function(
            self,
            "aws-challenge-delete-vpc-lambda",
            function_name="aws-challenge-delete-vpc-lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_14,
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda/delete_vpc"),
            environment={
                "TABLE_NAME": dynamodb_table.table_name,
            },
        )

        # 3.4 Create a lambda function for health check
        health_check_lambda = aws_lambda.Function(
            self,
            "aws-challenge-health-check-lambda",
            function_name="aws-challenge-health-check-lambda",
            runtime=aws_lambda.Runtime.PYTHON_3_14,
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda/health_check"),
        )
      

        # 3.3 Grant the Lambda functions required permissions
        dynamodb_table.grant_read_write_data(create_vpc_lambda)
        dynamodb_table.grant_read_write_data(get_all_vpc_lambda)
        dynamodb_table.grant_read_write_data(delete_vpc_lambda)

        create_vpc_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonVPCFullAccess")
        )
        delete_vpc_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonVPCFullAccess")
        )
        

        # 4. Create an API Gateway REST API that is protected by the Cognito User Pool authorizer

        # 4.1. Create an API Gateway REST API
        api = apigateway.RestApi(self, "aws-challenge-api",
            rest_api_name="aws-challenge-api",
            description="This is the AWS Challenge API",
            
            # This causes CDK to create a deployment + stage.
            deploy=True,
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                metrics_enabled=True,
                tracing_enabled=True,
            ),
        )

        # 4.2. Create a Cognito User Pool authorizer for the API Gateway
        authorizer = apigateway.CognitoUserPoolsAuthorizer(self, "aws-challenge-authorizer",
            cognito_user_pools=[userpool],
        )

        # 4.3. Create resources for the API Gateway
        api_resource = api.root.add_resource("api")
        vpc_resource = api.root.add_resource("vpcs")
        health_check_resource = api_resource.add_resource("health")

        # 4.4. Add methods to the API Gateway resources
        vpc_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(get_all_vpc_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        vpc_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(create_vpc_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        vpc_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(delete_vpc_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        health_check_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(health_check_lambda),
            authorization_type=apigateway.AuthorizationType.NONE,
        )

        ## Output the API URL and Cognito User Pool ID for testing
        cdk.CfnOutput(self, "ApiUrl", value=api.url)
        cdk.CfnOutput(self, "UserPoolId", value=userpool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientId", value=app_client.user_pool_client_id)
        cdk.CfnOutput(self, "DynamoDBTableName", value=dynamodb_table.table_name)

                      

       

## TODO
# 0. Manually create API gateway - Done
# 1. Lambda functions - Done
# 2. IAM roles for lambda functions - Done
# 3. Pylint 
# 4. Documentation 
# 5. Remove unit tests       