# from pydantic_settings import BaseSettings, SettingsConfigDict
#
#
# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", extra="ignore")
#
#     database_url: str
#     llm_api_key: str = ""
#     embedding_model: str = "BAAI/bge-small-en-v1.5"
#     embedding_dim: int = 384
#
#
# settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    llm_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384


settings = Settings()