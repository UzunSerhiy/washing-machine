from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Washing Machine"
    DATABASE_URL: str

    SERIAL_PORT: str = "/dev/ttyUSB0"
    BAUDTATE: int = 9600

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
