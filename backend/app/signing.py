"""Compliance signing.

After a request passes policy the gateway issues a short-lived ES256 token that
binds the verdict to the exact bytes forwarded upstream (SHA-256 of the body).
A downstream service that trusts the gateway's public key can verify the token
instead of running its own compliance checks. The token carries no prompt
content. The same key signs ledger entries.

The private key is read from SIGNING_KEY_PATH and generated on first start if
absent. For production the key should live in a KMS or HSM (see the roadmap).
"""
from __future__ import annotations

import base64
import hashlib
import time

import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from .config import settings

TOKEN_HEADER = "X-Compliance-Token"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def body_hash(body: bytes) -> str:
    return _b64url(hashlib.sha256(body).digest())


class Signer:
    def __init__(self) -> None:
        path = settings.signing_key_path
        if path.exists():
            self._key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._key = ec.generate_private_key(ec.SECP256R1())
            path.write_bytes(self._key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                     serialization.NoEncryption()))
            path.chmod(0o600)
        numbers = self._key.public_key().public_numbers()
        self._x = _b64url(numbers.x.to_bytes(32, "big"))
        self._y = _b64url(numbers.y.to_bytes(32, "big"))
        thumb = f'{{"crv":"P-256","kty":"EC","x":"{self._x}","y":"{self._y}"}}'
        self.kid = _b64url(hashlib.sha256(thumb.encode()).digest())[:16]

    def jwks(self) -> dict:
        return {"keys": [{"kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": self.kid,
                          "x": self._x, "y": self._y}]}

    def issue(self, *, request_id: str, subject: str, app: str, policy_id: str, policy_version: int, mode: str,
              decision: str, body: bytes) -> str:
        now = int(time.time())
        claims = {
            "iss": settings.signing_issuer, "aud": settings.signing_audience,
            "iat": now, "nbf": now - 5, "exp": now + settings.signing_ttl,
            "jti": request_id, "sub": subject, "app": app,
            "pol": {"id": policy_id, "ver": policy_version, "mode": mode},
            "dec": decision, "bh": body_hash(body),
        }
        return jwt.encode(claims, self._key, algorithm="ES256", headers={"kid": self.kid})

    def sign(self, data: bytes) -> str:
        return _b64url(self._key.sign(data, ec.ECDSA(hashes.SHA256())))

    def verify(self, data: bytes, signature: str) -> bool:
        try:
            raw = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
            self._key.public_key().verify(raw, data, ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError):
            return False


signer = Signer()
