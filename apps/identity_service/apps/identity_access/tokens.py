import base64
import hashlib
import hmac
import json
import time

from django.conf import settings


def _base64url_encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def create_access_token(user):
    issued_at = int(time.time())
    payload = {
        "companyId": str(user.company_id),
        "exp": issued_at + settings.AUTH_TOKEN_TTL_SECONDS,
        "iat": issued_at,
        "role": user.role,
        "sub": str(user.id),
    }
    header = {"alg": "HS256", "typ": "JWT"}

    encoded_header = _base64url_encode(
        json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )
    encoded_payload = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"),
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        settings.AUTH_TOKEN_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"

