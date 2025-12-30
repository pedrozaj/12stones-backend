"""R2/S3 storage utilities."""

import uuid
from io import BytesIO

import boto3
from botocore.config import Config

from app.config import get_settings

settings = get_settings()


def configure_r2_cors():
    """Configure CORS on R2 bucket for direct uploads from frontend."""
    client = get_r2_client()

    cors_configuration = {
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST", "HEAD"],
                "AllowedOrigins": [
                    "http://localhost:3000",
                    "https://12stones.vercel.app",
                    "https://12stones-frontend.vercel.app",
                    "https://*.vercel.app",
                ],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3600,
            }
        ]
    }

    try:
        client.put_bucket_cors(
            Bucket=settings.r2_bucket_name,
            CORSConfiguration=cors_configuration,
        )
        print(f"CORS configured for bucket {settings.r2_bucket_name}")
        return True
    except Exception as e:
        print(f"Failed to configure CORS: {e}")
        return False


def get_r2_client():
    """Get R2 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


def upload_file_to_r2(
    file_data: bytes,
    filename: str,
    content_type: str,
    folder: str = "content",
) -> str:
    """Upload a file to R2 and return the key."""
    client = get_r2_client()

    # Generate unique key
    file_ext = filename.split(".")[-1] if "." in filename else ""
    unique_id = str(uuid.uuid4())
    key = f"{folder}/{unique_id}.{file_ext}" if file_ext else f"{folder}/{unique_id}"

    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=file_data,
        ContentType=content_type,
    )

    return key


def get_file_url(key: str) -> str:
    """Get a presigned URL for downloading a file."""
    client = get_r2_client()

    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": key},
        ExpiresIn=3600,  # 1 hour
    )

    return url


def generate_upload_url(filename: str, content_type: str, folder: str = "uploads") -> dict:
    """Generate a presigned URL for direct upload to R2.

    Returns dict with 'upload_url' and 'key' for the upload.
    """
    client = get_r2_client()

    # Generate unique key
    file_ext = filename.split(".")[-1] if "." in filename else ""
    unique_id = str(uuid.uuid4())
    key = f"{folder}/{unique_id}.{file_ext}" if file_ext else f"{folder}/{unique_id}"

    # Generate presigned URL for PUT
    url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.r2_bucket_name,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=3600,  # 1 hour to complete upload
    )

    return {"upload_url": url, "key": key}


def get_file_from_r2(key: str) -> bytes:
    """Download a file from R2 and return its contents."""
    client = get_r2_client()

    response = client.get_object(Bucket=settings.r2_bucket_name, Key=key)
    return response["Body"].read()


def delete_file_from_r2(key: str) -> bool:
    """Delete a file from R2."""
    client = get_r2_client()

    try:
        client.delete_object(Bucket=settings.r2_bucket_name, Key=key)
        return True
    except Exception:
        return False
