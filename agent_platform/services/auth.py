import requests
from typing import Dict, Optional
import os
from datetime import datetime, timedelta, timezone
from loguru import logger
from cache.redis_client import RedisClient
from config.redis_config import AUTH_TOKEN_KEY, AUTH_TOKEN_EXPIRY


class AuthService:
    """Service for handling API authentication."""

    TOKEN_KEY = AUTH_TOKEN_KEY
    TOKEN_EXPIRY = AUTH_TOKEN_EXPIRY

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.redis = RedisClient()
        self.tokens: Dict[str, Dict] = {
            "data": {"access_token": None, "refresh_token": None, "expires_at": None}
        }

    def _load_tokens_from_cache(self) -> bool:
        """Load tokens from Redis cache."""
        cached_tokens = self.redis.get(self.TOKEN_KEY, as_json=True)
        if cached_tokens:
            self.tokens = cached_tokens
            # Check if access token is still valid
            expires_at = datetime.fromisoformat(self.tokens["data"]["expires_at"])
            if expires_at > datetime.utcnow():
                logger.info("Loaded valid tokens from cache")
                return True
            logger.info("Cached tokens expired, refreshing...")
        return False

    def _save_tokens_to_cache(self):
        """Save tokens to Redis cache."""
        self.redis.set(self.TOKEN_KEY, self.tokens, expiry=self.TOKEN_EXPIRY)
        logger.info("Saved tokens to cache")

    def get_access_token(self) -> str:
        """Get current access token, refresh if needed."""
        if not self.tokens["data"]["access_token"]:
            if not self._load_tokens_from_cache():
                self.initialize_auth()
        return self.tokens["data"]["access_token"]

    def initialize_auth(self) -> bool:
        """Initialize authentication by getting initial access and refresh tokens.

        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        if self._load_tokens_from_cache():
            return True

        auth_data = {
            "user_number": os.getenv("USER_NUMBER"),
            "password": os.getenv("API_PASSWORD"),
        }

        try:
            response = requests.post(f"{self.base_url}/auth/login", json=auth_data)
            response.raise_for_status()
            self.tokens = response.json()
            # Add expires_at if not present
            if "expires_at" not in self.tokens["data"]:
                self.tokens["data"]["expires_at"] = (
                    datetime.utcnow() + timedelta(seconds=self.TOKEN_EXPIRY)
                ).isoformat()
            self._save_tokens_to_cache()
            logger.info("Authentication successful!")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False

    def get_auth_tokens(self) -> Dict[str, str]:
        """Gets authentication tokens from the login API.

        Returns:
            dict: A dictionary containing access and refresh tokens or error information.
        """
        auth_data = {
            "email": "skarthikc.dev@gmail.com",
            "password": "cUcsuv-majtyc-9gejfa",
        }

        try:
            response = requests.post(f"{self.base_url}/auth/login", json=auth_data)
            response.raise_for_status()
            tokens = response.json()
            self.tokens.update(tokens)
            return tokens
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return {"error": str(e)}

    def refresh_auth_token(self) -> Dict[str, str]:
        """Refreshes the access token using the refresh token.

        Returns:
            dict: A dictionary containing the new access and refresh tokens or error information.
        """
        if not self.tokens["data"]["refresh_token"]:
            return self.get_auth_tokens()

        try:
            response = requests.post(
                f"{self.base_url}/auth/refresh",
                headers={
                    "Authorization": f"Bearer {self.tokens['data']['refresh_token']}"
                },
            )
            response.raise_for_status()
            self.tokens.update(response.json())
            self._save_tokens_to_cache()
            return self.tokens
        except Exception:
            return self.get_auth_tokens()

    def get_headers(self) -> Dict[str, str]:
        """Get headers with current access token.

        Returns:
            dict: Headers dictionary with Authorization
        """
        return {"Authorization": f"Bearer {self.tokens['data']['access_token']}"}
