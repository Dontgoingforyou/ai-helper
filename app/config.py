from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_api_key: str = ""
    ai_base_url: str = "https://api.groq.com/openai/v1"
    ai_model: str = "openai/gpt-oss-120b"
    ai_temperature: float = 0.2
    ai_max_tokens: int = 4000
    ai_timeout: float = 90
    ai_retries: int = 2


def get_settings() -> Settings:
    return Settings()
