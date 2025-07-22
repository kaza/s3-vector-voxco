import pytest
import boto3
from botocore.exceptions import ClientError


def test_aws_credentials_are_valid():
    """Test that AWS credentials are properly configured"""
    client = boto3.client('sts')
    try:
        response = client.get_caller_identity()
        assert 'Account' in response
        assert 'UserId' in response
        print(f"✓ Connected to AWS Account: {response['Account']}")
    except ClientError as e:
        pytest.fail(f"AWS credentials are not valid: {e}")


def test_aws_region_is_configured():
    """Test that AWS region is set"""
    session = boto3.Session()
    region = session.region_name
    assert region is not None, "AWS region is not configured"
    assert region in ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1', 'ap-northeast-1'], \
        f"Region {region} may not support S3 Vectors"
    print(f"✓ Using region: {region}")


def test_can_create_s3_client():
    """Test that we can create an S3 client"""
    try:
        client = boto3.client('s3')
        # Try to list buckets to verify permissions
        response = client.list_buckets()
        print(f"✓ Can access S3, found {len(response.get('Buckets', []))} buckets")
    except ClientError as e:
        pytest.fail(f"Cannot create S3 client: {e}")