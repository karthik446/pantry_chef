import os
import requests
from typing import Dict, Any
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PantryChefAPIClient:
    def __init__(self):
        self.base_url = "http://pantry-chef-api.default.svc.cluster.local:8000"
        self.token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"

    def _get_service_token(self) -> str:
        try:
            with open(self.token_path, "r") as f:
                token = f.read().strip()
                token_preview = f"{token[:20]}...{token[-20:]}"
                logger.info(f"Service account token loaded from {self.token_path}")
                logger.info(f"Token preview: {token_preview}")
                logger.info(f"Token length: {len(token)}")
                return token
        except Exception as e:
            logger.error(
                f"Failed to read service account token from {self.token_path}: {e}"
            )
            raise

    def create_recipe(self, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new recipe using the internal API endpoint
        """
        try:
            token = self._get_service_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/api/v1/internal/recipes"
            logger.info(f"Making request to: {url}")
            logger.info(f"Authorization header: Bearer {token[:20]}...{token[-20:]}")

            response = requests.post(url, json=recipe_data, headers=headers)

            if response.status_code == 401:
                logger.error("Authentication failed")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response body: {response.text}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create recipe: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                logger.error(f"Response body: {e.response.text}")
            raise
