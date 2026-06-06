import boto3
from botocore.exceptions import ClientError


def get_s3_client(app=None):
    """Return a boto3 S3 client using app configuration."""
    if app is None:
        from flask import current_app
        app = current_app

    return boto3.client(
        's3',
        aws_access_key_id=app.config.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=app.config.get('AWS_SECRET_ACCESS_KEY'),
        region_name=app.config.get('AWS_REGION'),
    )


def upload_file(local_path: str, bucket: str, key: str, client=None):
    """Upload a local file to the given S3 bucket and key."""
    if client is None:
        client = get_s3_client()
    client.upload_file(local_path, bucket, key)


def generate_presigned_url(bucket: str, key: str, expiration: int = 3600, client=None) -> str | None:
    """Generate a presigned URL to download the S3 object."""
    if client is None:
        client = get_s3_client()
    try:
        return client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration,
        )
    except ClientError:
        return None
