import requests
from typing import Dict, Optional


class AuthService:
    """Service for handling API authentication."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.tokens: Dict[str, Optional[str]] = {
            "access_token": None,
            "refresh_token": None,
        }

    def get_access_token(self) -> str:
        return self.tokens["access_token"]

    def initialize_auth(self) -> bool:
        """Initialize authentication by getting initial access and refresh tokens.

        Returns:
            bool: True if authentication was successful, False otherwise.
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
            print("Authentication successful!")
            return True
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
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
        if not self.tokens["refresh_token"]:
            return self.get_auth_tokens()

        try:
            response = requests.post(
                f"{self.base_url}/auth/refresh",
                headers={"Authorization": f"Bearer {self.tokens['refresh_token']}"},
            )
            response.raise_for_status()
            tokens = response.json()
            self.tokens.update(tokens)
            return tokens
        except Exception:
            return self.get_auth_tokens()

    def get_headers(self) -> Dict[str, str]:
        """Get headers with current access token.

        Returns:
            dict: Headers dictionary with Authorization
        """
        return {"Authorization": f"Bearer {self.tokens['access_token']}"}
