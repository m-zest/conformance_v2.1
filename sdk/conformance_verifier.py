"""Verify Conformance compliance tokens in a downstream service.

A model server, MCP server or internal API that should only accept requests
that passed the gateway can verify the X-Compliance-Token header instead of
running its own content checks. The token is an ES256 JWT that binds the
gateway's verdict to the exact request body (claim "bh" is the base64url
SHA-256 of the body).

Dependencies: pyjwt[crypto]

    from conformance_verifier import ComplianceVerifier, ComplianceError

    verifier = ComplianceVerifier(jwks_url="http://gateway:8000/.well-known/jwks.json")

    @app.post("/v1/chat/completions")
    async def completions(request: Request):
        body = await request.body()
        try:
            claims = verifier.verify(request.headers.get("x-compliance-token"), body)
        except ComplianceError as exc:
            return JSONResponse({"error": str(exc)}, status_code=401)
        ...
"""
from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
import urllib.request

import jwt

HEADER = "X-Compliance-Token"


class ComplianceError(Exception):
    pass


class ComplianceVerifier:
    def __init__(self, jwks_url: str | None = None, jwks: dict | None = None, issuer: str = "conformance-gateway",
                 audience: str = "llm-upstream", leeway: int = 10, refresh_seconds: int = 300) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self.leeway = leeway
        self.refresh_seconds = refresh_seconds
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched = 0.0
        self._lock = threading.Lock()
        if jwks:
            self._load(jwks)
            self._fetched = float("inf")

    def _load(self, jwks: dict) -> None:
        self._keys = {k["kid"]: jwt.PyJWK(k) for k in jwks.get("keys", [])}

    def _refresh(self) -> None:
        with self._lock:
            if time.monotonic() - self._fetched < 5:
                return
            with urllib.request.urlopen(self.jwks_url, timeout=5) as resp:  # noqa: S310 (operator-supplied URL)
                self._load(json.loads(resp.read()))
            self._fetched = time.monotonic()

    def _key(self, kid: str | None):
        stale = time.monotonic() - self._fetched > self.refresh_seconds
        if self.jwks_url and (kid not in self._keys or stale):
            try:
                self._refresh()
            except Exception as exc:
                if kid not in self._keys:
                    raise ComplianceError(f"gateway signing keys are not reachable: {exc}") from exc
        key = self._keys.get(kid)
        if key is None:
            raise ComplianceError("compliance token was signed with an unknown key")
        return key.key

    def verify(self, token: str | None, body: bytes) -> dict:
        """Return the token claims if the token is valid for this exact body, otherwise raise ComplianceError."""
        if not token:
            raise ComplianceError("missing compliance token: this endpoint only accepts requests from the AI gateway")
        try:
            kid = jwt.get_unverified_header(token).get("kid")
            claims = jwt.decode(token, self._key(kid), algorithms=["ES256"], issuer=self.issuer,
                                audience=self.audience, leeway=self.leeway)
        except jwt.PyJWTError as exc:
            raise ComplianceError(f"compliance token rejected: {exc}") from exc
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
        if claims.get("bh") != digest:
            raise ComplianceError("request body does not match the body that was checked by the gateway")
        return claims
