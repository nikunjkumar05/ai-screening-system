from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str = "sqlite:///./candidate_screening.db"
    mistral_api_key: str = ""
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
