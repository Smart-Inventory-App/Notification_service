from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    FIREBASE_CREDENTIALS: str

    class Config:
        env_file = ".env"


settings = Settings()
