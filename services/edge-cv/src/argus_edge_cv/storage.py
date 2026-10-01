"""Only read stream-prep objects from the configured bucket and tenant prefix."""

from urllib.parse import urlsplit


class FrameLoader:
    def __init__(self, client, bucket):
        self.client, self.bucket = client, bucket
        self.identity = None

    def __call__(self, uri):
        import cv2
        import numpy as np

        parsed = urlsplit(uri)
        key = parsed.path.lstrip("/")
        prefix = "/".join(self.identity) + "/"
        if (
            parsed.scheme != "s3"
            or parsed.netloc != self.bucket
            or not key.startswith(prefix)
        ):
            raise ValueError("frame storage scope mismatch")
        if any(part in (".", "..") for part in key.split("/")):
            raise ValueError("invalid object key")
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except (
            Exception
        ) as exc:  # Inspect S3 codes without coupling injected clients to boto3.
            error = getattr(exc, "response", {}).get("Error", {})
            if str(error.get("Code")) in {"NoSuchKey", "404", "NotFound"}:
                raise ValueError("frame expired or missing") from None
            raise
        body = response["Body"]
        try:
            raw = body.read(16 * 1024 * 1024 + 1)
        finally:
            body.close()
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError("frame exceeds size limit")
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("invalid image")
        return image
