from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(default="CHANGE_ME", validation_alias="BOT_TOKEN")
    database_path: str = Field(default="bot_data.db", validation_alias="DATABASE_PATH")
    timezone: str = Field(default="Europe/Moscow", validation_alias="TIMEZONE")
    roast_probability: float = Field(default=0.20, validation_alias="ROAST_PROBABILITY")
    auto_detect_drinks: bool = Field(default=False, validation_alias="AUTO_DETECT_DRINKS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

