from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings for the Recipe Engine.

    Attributes:
        API_BASE_URL: Base URL for the backend API
        API_EMAIL: Email for API authentication
        API_PASSWORD: Password for API authentication
        REDIS_URL: URL for Redis cache connection
    """

    API_BASE_URL: str = "http://localhost:8000/api"
    API_EMAIL: str = "admin@example.com"
    API_PASSWORD: str = "admin123"
    REDIS_URL: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields in the environment


# Create a global settings instance
settings = Settings()
