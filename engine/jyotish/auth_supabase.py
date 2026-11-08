"""Supabase Auth (login) -> organisation.

A signed-in user sends `Authorization: Bearer <access_token>`. We verify the token
locally (no network call per request) and map the user to a personal organisation,
created on first login. Everything downstream (quota, saved people) then works on
that organisation exactly as for an API key.

Config (env):
  SUPABASE_URL         https://<ref>.supabase.co   (JWKS is fetched from it: new projects, ES256/RS256)
  SUPABASE_JWT_SECRET  legacy HS256 shared secret  (only if the project still uses it)
Tokens must have aud=authenticated and not be expired.
"""
from __future__ import annotations

import os

import jwt

_jwks_client = None


def _key_for(token: str):
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        if not secret:
            raise jwt.InvalidTokenError("HS256 token but SUPABASE_JWT_SECRET is not set")
        return secret, ["HS256"]
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    if not url:
        raise jwt.InvalidTokenError("SUPABASE_URL is not set")
    global _jwks_client
    if _jwks_client is None or _jwks_client.uri != f"{url}/auth/v1/.well-known/jwks.json":
        _jwks_client = jwt.PyJWKClient(f"{url}/auth/v1/.well-known/jwks.json", cache_keys=True)
    if alg not in ("ES256", "RS256"):
        raise jwt.InvalidTokenError("unsupported token algorithm")
    return _jwks_client.get_signing_key_from_jwt(token).key, [alg]


def verify(token: str, key_resolver=None) -> dict | None:
    """-> {'user_id', 'email'} for a valid Supabase access token, else None."""
    try:
        key, algs = (key_resolver or _key_for)(token)
        claims = jwt.decode(token, key, algorithms=algs, audience="authenticated",
                            options={"require": ["exp", "sub"]})
    except (jwt.PyJWTError, ValueError, OSError):
        return None
    return {"user_id": claims["sub"], "email": claims.get("email", "")}


def bearer(headers) -> str | None:
    h = headers.get("Authorization") or headers.get("authorization") or ""
    return h[7:].strip() if h.lower().startswith("bearer ") else None
