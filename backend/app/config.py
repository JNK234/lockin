# ABOUTME: Application settings loaded from environment variables
# ABOUTME: Uses pydantic-settings for type-safe config management

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "lockin2026"

    openai_api_key: str = ""

    rocketride_uri: str = "http://localhost:5565"
    rocketride_apikey: str = ""
    rocketride_openai_key: str = ""

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
