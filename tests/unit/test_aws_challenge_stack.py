import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_challenge.aws_challenge_stack import AwsChallengeStack

def test_user_pool_uses_email_only():
    app = core.App()
    stack = AwsChallengeStack(app, "aws-challenge")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::Cognito::UserPool", {
        "UsernameAttributes": ["email"],
        "AutoVerifiedAttributes": ["email"],
    })
