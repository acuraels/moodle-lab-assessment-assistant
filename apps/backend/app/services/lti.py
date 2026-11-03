import base64
import hashlib
import hmac
import time
from urllib.parse import quote, urlsplit

from fastapi import Request

from app.config import settings


def _encoded(value: str) -> str:
    return quote(value, safe="~-._")


def _base_url(request: Request) -> str:
    url = str(request.url)
    if request.headers.get("x-forwarded-proto") == "https":
        url = url.replace("http://", "https://", 1)
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def verify_lti_request(request: Request, values: list[tuple[str, str]]) -> None:
    params = [(key, value) for key, value in values if key != "oauth_signature"]
    signature = next((value for key, value in values if key == "oauth_signature"), None)
    consumer_key = next((value for key, value in values if key == "oauth_consumer_key"), None)
    if not signature or consumer_key != settings.lti_consumer_key:
        raise ValueError("invalid signature or consumer")
    timestamp = next((value for key, value in values if key == "oauth_timestamp"), None)
    if timestamp and abs(time.time() - int(timestamp)) > settings.lti_timestamp_tolerance_seconds:
        raise ValueError("request timestamp is expired")
    normalized = "&".join(
        f"{_encoded(key)}={_encoded(value)}"
        for key, value in sorted(params, key=lambda item: (_encoded(item[0]), _encoded(item[1])))
    )
    base_string = "&".join(("POST", _encoded(_base_url(request)), _encoded(normalized)))
    signing_key = f"{_encoded(settings.lti_consumer_secret)}&"
    expected = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("invalid signature")
