# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "DevAgent Swarm"
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "amazon.nova-pro-v1:0"
    BEDROCK_SUPERVISOR_AGENT_ID: Optional[str] = None
    BEDROCK_AGENT_ALIAS_ID: Optional[str] = None

    DATABASE_URL: str = "postgresql://devagent:devagent@localhost:5432/devagent"
    DATABASE_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
