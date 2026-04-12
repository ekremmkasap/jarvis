from __future__ import annotations

from typing import Any

try:
    from .aws_common import aws_client, isoformat_or_none, log_cloud_operation, sanitize_text
except ImportError:  # pragma: no cover - used by standalone smoke imports
    from aws_common import aws_client, isoformat_or_none, log_cloud_operation, sanitize_text  # type: ignore


def list_buckets() -> list[dict[str, Any]] | dict[str, Any]:
    try:
        client = aws_client("s3")
        response = client.list_buckets()
        buckets = []
        for bucket in response.get("Buckets", []):
            name = str(bucket.get("Name") or "")
            buckets.append(
                {
                    "name": name,
                    "region": _bucket_region(client, name),
                    "creation_date": isoformat_or_none(bucket.get("CreationDate")),
                }
            )
        log_cloud_operation("s3", "list_buckets", {"count": len(buckets)})
        return buckets
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "list_buckets_failed", {"error": error})
        return {"ok": False, "error": error}


def list_objects(bucket: str, prefix: str = "") -> list[dict[str, Any]] | dict[str, Any]:
    try:
        client = aws_client("s3")
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
        objects = [
            {
                "key": str(item.get("Key") or ""),
                "size_bytes": int(item.get("Size") or 0),
                "last_modified": isoformat_or_none(item.get("LastModified")),
            }
            for item in response.get("Contents", [])
        ]
        log_cloud_operation("s3", "list_objects", {"bucket": bucket, "prefix": prefix, "count": len(objects)})
        return objects
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "list_objects_failed", {"bucket": bucket, "prefix": prefix, "error": error})
        return {"ok": False, "error": error}


def get_bucket_size(bucket: str) -> dict[str, Any]:
    try:
        client = aws_client("s3")
        total_size_bytes = 0
        object_count = 0
        continuation_token: str | None = None

        while True:
            params: dict[str, Any] = {"Bucket": bucket, "MaxKeys": 1000}
            if continuation_token:
                params["ContinuationToken"] = continuation_token
            response = client.list_objects_v2(**params)
            for item in response.get("Contents", []):
                total_size_bytes += int(item.get("Size") or 0)
                object_count += 1
            if not response.get("IsTruncated"):
                break
            continuation_token = str(response.get("NextContinuationToken") or "")
            if not continuation_token:
                break

        payload = {"total_size_bytes": total_size_bytes, "object_count": object_count}
        log_cloud_operation("s3", "get_bucket_size", {"bucket": bucket, **payload})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "get_bucket_size_failed", {"bucket": bucket, "error": error})
        return {"ok": False, "error": error}


def upload_file(bucket: str, key: str, local_path: str) -> dict[str, Any]:
    try:
        client = aws_client("s3")
        client.upload_file(local_path, bucket, key)
        region = _bucket_region(client, bucket)
        payload = {"ok": True, "url": _object_url(bucket, key, region)}
        log_cloud_operation("s3", "upload_file", {"bucket": bucket, "key": key, "ok": True})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "upload_file_failed", {"bucket": bucket, "key": key, "error": error})
        return {"ok": False, "error": error}


def delete_object(bucket: str, key: str) -> dict[str, Any]:
    try:
        client = aws_client("s3")
        client.delete_object(Bucket=bucket, Key=key)
        payload = {"ok": True, "message": f"Object deleted: {key}"}
        log_cloud_operation("s3", "delete_object", {"bucket": bucket, "key": key, "ok": True})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "delete_object_failed", {"bucket": bucket, "key": key, "error": error})
        return {"ok": False, "error": error}


def generate_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> dict[str, Any]:
    try:
        client = aws_client("s3")
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=int(expires_in),
        )
        payload = {
            "ok": True,
            "url": str(url),
            "expires_in": int(expires_in),
            "bucket": bucket,
            "key": key,
        }
        log_cloud_operation("s3", "generate_presigned_url", {"bucket": bucket, "key": key, "expires_in": int(expires_in)})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "generate_presigned_url_failed", {"bucket": bucket, "key": key, "error": error})
        return {"ok": False, "error": error}


def get_object_metadata(bucket: str, key: str) -> dict[str, Any]:
    try:
        client = aws_client("s3")
        response = client.head_object(Bucket=bucket, Key=key)
        payload = {
            "ok": True,
            "content_type": str(response.get("ContentType") or "unknown"),
            "size_bytes": int(response.get("ContentLength") or 0),
            "last_modified": isoformat_or_none(response.get("LastModified")) or "",
        }
        log_cloud_operation("s3", "get_object_metadata", {"bucket": bucket, "key": key, "ok": True})
        return payload
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("s3", "get_object_metadata_failed", {"bucket": bucket, "key": key, "error": error})
        return {"ok": False, "error": error}


def _bucket_region(client: Any, bucket: str) -> str:
    response = client.get_bucket_location(Bucket=bucket)
    location = response.get("LocationConstraint")
    return str(location or "us-east-1")


def _object_url(bucket: str, key: str, region: str) -> str:
    if region == "us-east-1":
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
