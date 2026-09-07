from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from argus.services import storage


@pytest.mark.asyncio
async def test_presigned_url_uses_public_host_and_sigv4():
    storage._public_s3_client.cache_clear()
    with patch.object(storage.settings, "s3_public_endpoint_url", "https://api.storage.argus.ferredemo.dev"), \
         patch.object(storage.settings, "s3_access_key_id", "test"), \
         patch.object(storage.settings, "s3_secret_access_key", "test"), \
         patch.object(storage.settings, "s3_bucket_name", "argus"):
        url = urlsplit(await storage.generate_presigned_get_url("folder/frame.jpg"))
        assert url.netloc == "api.storage.argus.ferredemo.dev"
        assert url.path == "/argus/folder/frame.jpg"
        assert parse_qs(url.query)["X-Amz-Algorithm"] == ["AWS4-HMAC-SHA256"]
    storage._public_s3_client.cache_clear()


def test_local_development_keeps_existing_client():
    storage._public_s3_client.cache_clear()
    with patch.object(storage.settings, "s3_public_endpoint_url", ""), patch.object(storage, "_s3_client") as internal:
        assert storage._public_s3_client() is internal.return_value
    storage._public_s3_client.cache_clear()
