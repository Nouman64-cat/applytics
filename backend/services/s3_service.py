import boto3

from core.config import get_settings

DEFAULT_PRESIGNED_URL_EXPIRY_SECONDS = 900


def _client():
    settings = get_settings()
    if not (settings.aws_access_key_id and settings.aws_secret_access_key and settings.aws_s3_region):
        raise RuntimeError("AWS S3 credentials not configured in .env")
    return boto3.client(
        "s3",
        region_name=settings.aws_s3_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        # boto3 defaults to the global s3.amazonaws.com endpoint for presigned URLs
        # regardless of region_name, which 307-redirects for any bucket outside
        # us-east-1 (confirmed live against this bucket, which is ap-south-1) —
        # pin the endpoint explicitly so presigned URLs work without a redirect hop.
        endpoint_url=f"https://s3.{settings.aws_s3_region}.amazonaws.com",
    )


def _bucket() -> str:
    settings = get_settings()
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME not configured in .env")
    return settings.s3_bucket_name


def upload_file(key: str, content: bytes, content_type: str) -> None:
    _client().put_object(Bucket=_bucket(), Key=key, Body=content, ContentType=content_type)


def generate_presigned_url(key: str, expires_in: int = DEFAULT_PRESIGNED_URL_EXPIRY_SECONDS) -> str:
    return _client().generate_presigned_url(
        "get_object", Params={"Bucket": _bucket(), "Key": key}, ExpiresIn=expires_in
    )


def delete_file(key: str) -> None:
    _client().delete_object(Bucket=_bucket(), Key=key)
