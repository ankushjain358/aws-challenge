from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_lambda,
    aws_iam as iam,
)
import aws_cdk as cdk
from constructs import Construct

class ApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_runtime = aws_lambda.Runtime.PYTHON_3_14
        lambda_architecture = aws_lambda.Architecture.ARM_64
        lambda_timeout = cdk.Duration.seconds(30)
        powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            "AwsLambdaPowertoolsPythonLayer",
            f"arn:aws:lambda:{cdk.Aws.REGION}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python314-arm64:38",
        )

        # 1.1. Create a Cognito User Pool with minimal configuration
        userpool = cognito.UserPool(self, "aws-challenge-user-pool",
            user_pool_name="aws-challenge-user-pool",
            sign_in_aliases=cognito.SignInAliases(email=True, username=False, phone=False, preferred_username=False),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=cdk.RemovalPolicy.DESTROY,  # NOT recommended for production
        )

        # 1.2. Create an app client for the user pool with user password flow enabled
        # Note:Keeping user password flow instead of OAuth flow for now for the simplicity of the challenge
        app_client = userpool.add_client("aws-challenge-app-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
            )
        )

        # 2. Create a DynamoDB table with a primary key of "id".
        dynamodb_table = dynamodb.Table(self, "aws-challenge-metadata-table",
            table_name="aws-challenge-metadata-table",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            removal_policy=cdk.RemovalPolicy.DESTROY,  # NOT recommended for production
        )

        # 3. Lambda functions

        # 3.1 Create a Lambda function to create a VPC and store its metadata in DynamoDB
        create_vpc_lambda = aws_lambda.Function(
            self,
            "aws-challenge-create-vpc-lambda",
            function_name="aws-challenge-create-vpc-lambda",
            runtime=lambda_runtime,
            architecture=lambda_architecture,
            timeout=lambda_timeout,
            layers=[powertools_layer],
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
            runtime=lambda_runtime,
            architecture=lambda_architecture,
            timeout=lambda_timeout,
            layers=[powertools_layer],
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda/get_all_vpc"),
            environment={
                "TABLE_NAME": dynamodb_table.table_name,
            },
        )

        # 3.3 Create a lambda function to delete a VPC and its metadata from DynamoDB
        delete_vpc_lambda = aws_lambda.Function(
            self,
            "aws-challenge-delete-vpc-lambda",
            function_name="aws-challenge-delete-vpc-lambda",
            runtime=lambda_runtime,
            architecture=lambda_architecture,
            timeout=lambda_timeout,
            layers=[powertools_layer],
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
            runtime=lambda_runtime,
            architecture=lambda_architecture,
            timeout=lambda_timeout,
            layers=[powertools_layer],
            handler="handler.lambda_handler",
            code=aws_lambda.Code.from_asset("lambda/health_check"),
        )

        # 3.6 Grant the Lambda functions required permissions
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
        health_check_resource = api_resource.add_resource("health")
        vpc_resource = api_resource.add_resource("vpcs")
        delete_vpc_resource = vpc_resource.add_resource("{vpc_id}")

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

        delete_vpc_resource.add_method(
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

        ## 5. Output the API URL and Cognito User Pool ID for testing
        cdk.CfnOutput(self, "ApiUrl", value=api.url)
        cdk.CfnOutput(self, "UserPoolId", value=userpool.user_pool_id)
        cdk.CfnOutput(self, "UserPoolClientId", value=app_client.user_pool_client_id)
