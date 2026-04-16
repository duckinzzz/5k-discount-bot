import base64
import http.cookiejar
import json
import time
from pathlib import Path
from typing import Any

from curl_cffi import requests

from config import HTTP_TIMEOUT_SECONDS, X5_WEB_COOKIES_PATH
from core import logger

WEB_SESSION_URL = "https://5ka.ru/api/auth/session"
BROWSER_IMPERSONATION = "chrome136"
WEB_SESSION_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ru,en;q=0.9",
    "referer": "https://5ka.ru/profile/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}
LOYALTY_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "user-agent": WEB_SESSION_HEADERS["user-agent"],
}
GET_CARDS_URL = "https://gw-ly5.x5.ru/api/cards/el5.cards.CardsService/GetCards"
GET_BARCODE_URL = "https://gw-ly5.x5.ru/api/cards/el5.cards.CardsService/GetBarCode"
TOKEN_REFRESH_SKEW_SECONDS = 60
CARD_TYPE_PRIORITY = {
    "VIPCLUB": 0,
    "X5VC": 1,
    "VC5": 2,
    "TC5": 3,
    "YCC": 4,
    "X5BN": 5,
    "X5BU": 6,
    "PBCB": 7,
    "5ACB": 8,
    "USPC": 9,
    "TSPC": 10,
    "UCSR": 11,
    "ZOZH": 12,
}


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


class X5WebClient:
    def __init__(self, cookies_path: Path) -> None:
        self._cookies_path = cookies_path
        self._session_token: str | None = None
        self._session_token_expires_at = _parse_expiry(None)

    def _load_cookies(self) -> http.cookiejar.MozillaCookieJar:
        jar = http.cookiejar.MozillaCookieJar(str(self._cookies_path))
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar

    def _persist_cookies(self, cookies: http.cookiejar.CookieJar) -> None:
        jar = http.cookiejar.MozillaCookieJar(str(self._cookies_path))
        for cookie in cookies:
            jar.set_cookie(cookie)
        jar.save(ignore_discard=True, ignore_expires=True)

    def _session_token_is_valid(self) -> bool:
        if not self._session_token:
            return False

        if self._session_token_expires_at is None:
            return True

        return time.time() < self._session_token_expires_at - TOKEN_REFRESH_SKEW_SECONDS

    def _refresh_session_token(self) -> str:
        session = requests.Session(impersonate=BROWSER_IMPERSONATION)
        session.cookies.update(self._load_cookies())
        session.headers.update(WEB_SESSION_HEADERS)

        response = session.get(WEB_SESSION_URL, timeout=HTTP_TIMEOUT_SECONDS)
        response.raise_for_status()

        payload = response.json()
        token = payload.get("user", {}).get("token")
        if not token:
            raise RuntimeError(
                "5ka web session token is unavailable; refresh cookies-5ka-ru.txt",
            )

        self._persist_cookies(session.cookies.jar)
        self._session_token = token
        self._session_token_expires_at = _parse_expiry(token)
        logger.info("5ka web session token refreshed and cookies persisted")
        return token

    def get_session_token(self) -> str:
        if self._session_token_is_valid():
            return self._session_token

        return self._refresh_session_token()

    def _get_json(self, url: str) -> dict[str, Any]:
        response = requests.get(
            url,
            headers={
                **LOYALTY_HEADERS,
                "authorization": f"Bearer {self.get_session_token()}",
            },
            impersonate=BROWSER_IMPERSONATION,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def get_cards(self) -> list[dict[str, Any]]:
        data = self._get_json(GET_CARDS_URL)
        return data["data"]["cards"]

    def get_card_number(self) -> str:
        cards = self.get_cards()
        active_cards = [card for card in cards if card.get("cardStatus") == "ACTIVE"]
        if not active_cards:
            raise RuntimeError("Active 5ka loyalty card not found")

        card = min(
            active_cards,
            key=lambda item: CARD_TYPE_PRIORITY.get(item.get("cardType"), 999),
        )
        card_number = card.get("cardNo")
        if not card_number:
            raise RuntimeError("5ka loyalty card number is missing")

        return card_number

    def get_barcode_data(self, card_number: str | None = None) -> str:
        current_card_number = card_number or self.get_card_number()
        data = self._get_json(f"{GET_BARCODE_URL}/{current_card_number}")
        barcode = data["data"]["barcode"]
        if not barcode:
            raise RuntimeError("5ka barcode is missing")

        return barcode


x5_web_client = X5WebClient(cookies_path=X5_WEB_COOKIES_PATH)
