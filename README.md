# AWS Challenge 2026

## Problem Statement

## Architecture Diagram

## Prerequisites

## How to deploy the solution

## Verification of the solution

## Clean up the solution

## References
- Refer [Working with the AWS CDK in Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html) for more information.
- [Serverless Patterns Collection](https://serverlessland.com/patterns)

## Best practices
1. Always execute commands in a virtual environment to avoid dependency conflicts.
2. Your requirements.txt should list only top-level dependencies (modules that your app depends on directly) and not the dependencies of those libraries. To follow this, you can use the following steps:
    - Install packages using `pip install <package_name>`.
    - Run `pip show <package_name>` to view the package version and its dependencies.
    - Then manually add `<package_name>==2.32.5` to your `requirements.txt` file.
3. Developer experience
    - Use `pylance` to prevent type errors. Refer [preventing type errors](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html#python-managemodules)