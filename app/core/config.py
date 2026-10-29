from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    # URL https pública del logo que va arriba de los mails (vacío = mails sin logo)
    EMAIL_LOGO_URL: str = ""

    FIREBASE_CREDENTIALS: str

    class Config:
        env_file = ".env"


settings = Settings()
