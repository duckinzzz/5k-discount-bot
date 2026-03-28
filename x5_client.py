import base64
import json
import os
import threading
import time
from typing import Any

import requests
from dotenv import set_key

from config import (
    DOTENV_PATH,
    HTTP_TIMEOUT_SECONDS,
    X5M_ACCESS_TOKEN,
    X5M_API_BASE,
    X5M_CLIENT_ID,
    X5M_REFRESH_TOKEN,
    X5M_TOKEN_URL,
)
from core import logger

API_HEADERS = {
    "accept": "application/json",
    "x-capabilities": "tenant=ts5;clientVersion=3.29.0;divKitVersion=31.6.0;OS=Android/10;source=mob-app;teamId=x5m;timeZone=-5",
    "accept-charset": "UTF-8",
    "user-agent": "ktor-client",
    "host": "x5m.x5.ru",
    "connection": "Keep-Alive",
    "accept-encoding": "gzip",
}

TOKEN_HEADERS = {
    "accept": "application/json",
    "content-type": "application/x-www-form-urlencoded",
    "user-agent": "Dalvik/2.1.0 (Linux; U; Android 10; ONEPLUS A5000 Build/QKQ1.191014.012)",
}

TOKEN_REFRESH_SKEW_SECONDS = 60


def _decode_jwt_claims(token: str | None) -> dict[str, Any]:
    if not token:
        return {}

    try:
        payload = token.split(".")[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        return json.loads(decoded)
    except Exception:
        return {}


def _parse_expiry(token: str | None) -> int | None:
    claims = _decode_jwt_claims(token)
    exp = claims.get("exp")

    try:
        return int(exp) if exp is not None else None
    except (TypeError, ValueError):
        return None


class X5MobileClient:
    def __init__(
        self,
        access_token: str | None,
        refresh_token: str | None,
    ) -> None:
        self._lock = threading.Lock()
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._access_token_expires_at = _parse_expiry(access_token)

    def _build_headers(self, access_token: str, extra_headers: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            **API_HEADERS,
            "authorization": f"Bearer {access_token}",
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _access_token_is_valid(self) -> bool:
        if not self._access_token:
            return False

        if self._access_token_expires_at is None:
            return True

        return time.time() < self._access_token_expires_at - TOKEN_REFRESH_SKEW_SECONDS

    def _persist_tokens(self, access_token: str, refresh_token: str) -> None:
        os.environ["X5M_ACCESS_TOKEN"] = access_token
        os.environ["X5M_BEARER_TOKEN"] = access_token
        os.environ["X5M_REFRESH_TOKEN"] = refresh_token

        if not DOTENV_PATH.exists():
            return

        for key, value in (
            ("X5M_ACCESS_TOKEN", access_token),
            ("X5M_BEARER_TOKEN", access_token),
            ("X5M_REFRESH_TOKEN", refresh_token),
        ):
            set_key(
                str(DOTENV_PATH),
                key,
                value,
                quote_mode="never",
                encoding="utf-8",
            )

    def refresh_tokens(self, *, force: bool = False, failed_access_token: str | None = None) -> None:
        with self._lock:
            if failed_access_token and failed_access_token != self._access_token and self._access_token_is_valid():
                return

            if not force and self._access_token_is_valid():
                return

            if not self._refresh_token:
                raise RuntimeError("X5M_REFRESH_TOKEN is missing, cannot refresh expired access token")

            response = requests.post(
                X5M_TOKEN_URL,
                headers=TOKEN_HEADERS,
                data={
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                    "client_id": X5M_CLIENT_ID,
                },
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            payload = response.json()
            access_token = payload["access_token"]
            refresh_token = payload.get("refresh_token") or self._refresh_token

            self._access_token = access_token
            self._refresh_token = refresh_token
            self._access_token_expires_at = _parse_expiry(access_token)

            if self._access_token_expires_at is None:
                expires_in = payload.get("expires_in")
                if expires_in is not None:
                    self._access_token_expires_at = int(time.time()) + int(expires_in)

            self._persist_tokens(access_token, refresh_token)
            logger.info("X5M tokens refreshed")

    def get_access_token(self) -> str:
        if not self._access_token_is_valid():
            self.refresh_tokens()

        if not self._access_token:
            raise RuntimeError("X5M access token is unavailable")

        return self._access_token

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{X5M_API_BASE.rstrip('/')}/{path.lstrip('/')}"
        extra_headers = kwargs.pop("headers", None)

        access_token = self.get_access_token()
        response = requests.request(
            method,
            url,
            headers=self._build_headers(access_token, extra_headers),
            timeout=HTTP_TIMEOUT_SECONDS,
            **kwargs,
        )

        if response.status_code == 401:
            logger.warning("X5M API returned 401 for %s %s, refreshing tokens", method.upper(), path)
            response.close()
            self.refresh_tokens(force=True, failed_access_token=access_token)
            access_token = self.get_access_token()
            response = requests.request(
                method,
                url,
                headers=self._build_headers(access_token, extra_headers),
                timeout=HTTP_TIMEOUT_SECONDS,
                **kwargs,
            )

        return response

    def get_json(self, path: str, **kwargs) -> dict[str, Any]:
        response = self.request("GET", path, **kwargs)
        response.raise_for_status()
        return response.json()


x5_mobile_client = X5MobileClient(
    access_token=X5M_ACCESS_TOKEN,
    refresh_token=X5M_REFRESH_TOKEN,
)
