"""API client for MyLight150 integration with Home Assistant."""
from __future__ import annotations

from typing import Any
import base64
import hashlib
import logging
import secrets
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

import aiohttp
from aiohttp import ClientSession, ClientResponseError, ClientError
from urllib.parse import parse_qs
import jwt
from jwt.algorithms import RSAAlgorithm

from homeassistant.core import HomeAssistant

from .const import (
    OAUTH_URL,
    OAUTH_CLIENT_ID,
    OAUTH_SCOPE,
    OAUTH_POLICY_NAME,
    OAUTH_REDIRECT_URI,
    API_SUBSCRIPTION_KEY,
    API_URL,
    OAUTH_TENANT_NAME,
    OAUTH_TENANT_ID,
)

_LOGGER = logging.getLogger(__name__)


class MyLight150AuthError(Exception):
    """Raised when authentication fails (bad credentials, expired tokens...)."""


class MyLight150ApiError(Exception):
    """Raised when an API call fails."""


class MyLight150ApiClient:
    """Async client for the MyLight150 API."""

    def __init__(self, hass: HomeAssistant, session: ClientSession, username: str, password: str) -> None:
        self._hass = hass
        self._session = session
        self._username = username
        self._password = password
        # Token & token expiration storage
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: float = 0.0
        self._refresh_token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def async_login_test(self) -> bool:
        """Full OAuth2 PKCE login flow. Returns True on success."""
        _LOGGER.debug(f"Login test for account: {self._username}")
        try:
            self._access_token = await self._get_token_from_login()
            _LOGGER.debug("Login successful!")
            _LOGGER.debug((f"Access token: (validity: "
                           f"{datetime.fromtimestamp(self._token_expires_at, ZoneInfo("Europe/Paris")).strftime('%Y-%m-%d %H:%M:%S')} (Paris)) "
                           f"{self._access_token[:100]}..."))
            _LOGGER.debug((f"Refresh token: (validity: "
                           f"{datetime.fromtimestamp(self._refresh_token_expires_at, ZoneInfo("Europe/Paris")).strftime('%Y-%m-%d %H:%M:%S')} (Paris)) "
                           f"{self._refresh_token[:100]}..."))
            return self._access_token is not None
        except MyLight150AuthError:
            raise
        except Exception as err:
            raise MyLight150AuthError(f"Login failed: {err}") from err


    async def async_get_valid_token(self) -> str:
        """Return a valid access token, refreshing or re-logging if needed."""
        now = datetime.now(timezone.utc).timestamp()
        _LOGGER.debug((f"MyLight150: Now time : {now} /"            
                       f" Access token validity: {self._token_expires_at} /"
                       f" Refresh token validity: {self._refresh_token_expires_at}"))

        if self._access_token and self._token_expires_at > now:
            _LOGGER.debug(f"Token is still valid for account: {self._username} (token: {self._access_token[:20]}...)")
            return self._access_token

        if self._refresh_token and self._refresh_token_expires_at > now:
            _LOGGER.debug("MyLight150: Access token expired but refresh token still available, refreshing...")
            return await self._get_token_from_refresh()

        _LOGGER.debug("MyLight150: No valid token, performing full login...")
        return await self._get_token_from_login()
    

    async def async_call_api(self, endpoint: str) -> dict[str, Any]:
        """Call a MyLight150 API endpoint and return the JSON response."""
        token = await self.async_get_valid_token()
        url = f"{API_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Ocp-Apim-Subscription-Key": API_SUBSCRIPTION_KEY,
            "Accept": "application/json, text/plain, */*",
            "Origin": OAUTH_REDIRECT_URI,
            "Referer": OAUTH_REDIRECT_URI,
            "X-client-Type": "Web",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            async with self._session.get(url, headers=headers, timeout=10) as response:
                if response.status == 401:
                    raise MyLight150ApiError(f"Token rejected by API for {endpoint} ({response.status})")
                response.raise_for_status()

                return await response.json()
        except MyLight150AuthError:
            raise
        except ClientResponseError as err:
            raise MyLight150ApiError(f"API error {err.status} on {endpoint}") from err
        except ClientError as err:
            raise MyLight150ApiError(f"Connection error on {endpoint}: {err}") from err


    def restore_tokens(
        self,
        access_token: str,
        refresh_token: str,
        not_before: float,
        expires_in: int,
        refresh_token_expires_in: int,
    ) -> None:
        """Restore tokens previously persisted in the HA config entry."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at = not_before + expires_in
        self._refresh_token_expires_at = not_before + refresh_token_expires_in


    def get_token_data(self) -> dict[str, Any]:
        """Return token data suitable for persistence in the HA config entry."""
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "token_expires_at": self._token_expires_at,
            "refresh_token_expires_at": self._refresh_token_expires_at,
        }

    # ------------------------------------------------------------------
    # Token validation
    # ------------------------------------------------------------------

    async def _get_signing_key(self, token: str) -> Any:
        """Fetch JWKS and return the public key matching the token's kid."""
        jwks_url = f"{OAUTH_URL}/discovery/v2.0/keys"
        async with self._session.get(jwks_url) as response:
            response.raise_for_status()
            jwks_data = await response.json()

        header = jwt.get_unverified_header(token)
        kid = header["kid"]
        for key in jwks_data["keys"]:
            if key["kid"] == kid:
                return RSAAlgorithm.from_jwk(key)
        raise MyLight150AuthError(f"Public key not found for kid: {kid}")


    async def async_validate_token(self) -> bool:
        """Validate a JWT and return its decoded payload, or None if invalid."""
        try:
            if not self._access_token:
                _LOGGER.debug("MyLight150: No access token to validate")
                return False
            signing_key = await self._get_signing_key(self._access_token)

            _LOGGER.debug(f"MyLight150: Access token valid ({self._access_token[:50]})")
            return True
        except jwt.ExpiredSignatureError:
            _LOGGER.debug("MyLight150: Token expired")
            return False
        except jwt.InvalidTokenError as err:
            _LOGGER.debug("MyLight150: Invalid JWT: %s", err)
            return False


    # ------------------------------------------------------------------
    # OAuth2 PKCE login flow
    # ------------------------------------------------------------------

    async def _get_token_from_login(self) -> str:
        """Call full B2C login through request in a executor thread."""
        _LOGGER.debug(f"MyLight150: Starting executor thread to proceed to a full login for account: {self._username}")
        return await self._hass.async_add_executor_job(self._sync_login)

    def _sync_login(self) -> str:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        # PKCE
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")
        )

        # Step 1
        form_url = (
            f"{OAUTH_URL}/oauth2/v2.0/authorize?"
            f"client_id={OAUTH_CLIENT_ID}&"
            f"scope={OAUTH_SCOPE.replace(' ', '+')}&"
            f"redirect_uri={OAUTH_REDIRECT_URI}&"
            f"response_type=code&response_mode=fragment&"
            f"code_challenge={code_challenge}&code_challenge_method=S256"
        )
        _LOGGER.debug(f"MyLight150: Formular request URL: {form_url[:100]}...")

        response = session.get(form_url)
        if response.status_code != 200:
            _LOGGER.debug(f"MyLight150: Step 1 failed! Response code: {response.status_code}")
            _LOGGER.debug(f"Response text: {response.text[:200]}")
            raise MyLight150AuthError(f"MyLight150: Step 1 failed: {response.status_code}")

        csrf_token = session.cookies.get("x-ms-cpim-csrf")
        trans_token = session.cookies.get("x-ms-cpim-trans")
        if not csrf_token or not trans_token:
            _LOGGER.debug(f"Step 1: Missing token")
            raise MyLight150AuthError("Step 1: Missing token")

        # Step 2
        self_asserted_url = (
            f"{OAUTH_URL}/SelfAsserted?"
            f"tx=StateProperties={trans_token}&p={OAUTH_POLICY_NAME}"
        )
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-CSRF-TOKEN": csrf_token,
            "x-ms-cpim-csrf": csrf_token,
            "x-ms-cpim-trans": trans_token,
        }
        data = {
            "request_type": "RESPONSE",
            "signInName": self._username,
            "password": self._password,
        }
        _LOGGER.debug(f"MyLight150: Self asserted request URL: {self_asserted_url[:100]}...")

        response = session.post(self_asserted_url, data=data, headers=headers)
        if response.status_code != 200:
            _LOGGER.debug(f"MyLight150: Step 2 failed! Response code: {response.status_code}")
            _LOGGER.debug(f"MyLight150: Response text: {response.text[:200]}")
            raise MyLight150AuthError(f"Step 2 failed: {response.status_code}")

        # Step 3
        confirmation_url = (
            f"{OAUTH_URL}/api/CombinedSigninAndSignup/confirmed?"
            f"rememberMe=true&csrf_token={csrf_token}&"
            f"tx=StateProperties={trans_token}&"
            f"p={OAUTH_POLICY_NAME}&diags="
        )
        headers = {
            "X-CSRF-TOKEN": csrf_token,
            "x-ms-cpim-trans": trans_token,
        }
        _LOGGER.debug(f"Confirmation request URL: {confirmation_url[:100]}...")

        response = session.get(confirmation_url, headers=headers, allow_redirects=False)
        if response.status_code != 302:
            _LOGGER.debug(f"MyLight150: Step 3 failed! Response code: {response.status_code}")
            _LOGGER.debug(f"MyLight150: Response text: {response.text[:200]}")
            raise MyLight150AuthError(f"MyLight150: Step 3 failed: got {response.status_code}")

        redirect_url = response.headers.get("Location", "")
        fragment = redirect_url.split("#")[1]
        params = parse_qs(fragment)
        auth_code = params.get("code", [None])[0]
        if not auth_code:
            _LOGGER.debug(f"MyLight150: Step 3: Missing auth_code in redirect URL: {redirect_url[:100]}...")
            raise MyLight150AuthError(f"MyLight150: Step 3: Missing auth_code in redirect URL")

        # Step 4
        token_url = f"{OAUTH_URL}/oauth2/v2.0/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": OAUTH_CLIENT_ID,
            "scope": OAUTH_SCOPE,
            "code_verifier": code_verifier,
            "code": auth_code,
            "redirect_uri": OAUTH_REDIRECT_URI,
        }
        _LOGGER.debug(f"Token request URL: {token_url[:100]}...")

        response = session.post(token_url, data=data, allow_redirects=False)
        if response.status_code != 200:
            _LOGGER.debug(f"MyLight150: Step 4 failed! Response code: {response.status_code}")
            _LOGGER.debug(f"MyLight150: Response text: {response.text[:200]}")
            raise MyLight150AuthError(f"MyLight150: Step 4 failed: {response.status_code}")

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            _LOGGER.debug(f"MyLight150: Step 4: Missing access_token in response: {token_data[:100]}...")
            raise MyLight150AuthError(f"MyLight150: Step 4: Missing access_token in response")

        self._access_token = access_token
        self._refresh_token = token_data.get("refresh_token")
        not_before = float(token_data.get("not_before", 0))
        self._token_expires_at = not_before + int(token_data.get("expires_in", 3600))
        self._refresh_token_expires_at = not_before + int(
            token_data.get("refresh_token_expires_in", 0)
        )
        _LOGGER.debug(f"MyLight150: Successful login for account: {self._username}")
        return access_token


    # ------------------------------------------------------------------
    # Token refresh
    # ------------------------------------------------------------------

    async def _get_token_from_refresh(self) -> str:
        """Use refresh_token to get a new access_token."""
        url = f"{OAUTH_URL}/oauth2/v2.0/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": OAUTH_CLIENT_ID,
            "refresh_token": self._refresh_token,
            "scope": OAUTH_SCOPE,
        }

        try:
            async with self._session.post(url, data=data) as response:
                if response.status != 200:
                    _LOGGER.warning(f"MyLight150: Token refresh failed ({response.status}), will re-login")
                    return await self._get_token_from_login()
                token_data = await response.json()
        except ClientError as err:
            raise MyLight150ApiError(f"Token refresh connection error: {err}") from err

        access_token = token_data.get("access_token")
        if not access_token:
            return await self._get_token_from_login()

        self._access_token = access_token
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        not_before = float(token_data.get("not_before", 0))
        self._token_expires_at = not_before + int(token_data.get("expires_in", 3600))
        self._refresh_token_expires_at = not_before + int(
            token_data.get("refresh_token_expires_in", 0)
        )

        _LOGGER.debug("MyLight150: Token refreshed successfully")
        return access_token