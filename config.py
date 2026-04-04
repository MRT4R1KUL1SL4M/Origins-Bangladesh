import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    DB_HOST = os.getenv("DB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com")
    DB_PORT = int(os.getenv("DB_PORT", "4000"))
    DB_USER = os.getenv("DB_USER", "2cPo7b5N2rLWuv9.root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "P6S0HBGaSQY1gw74")
    DB_NAME = os.getenv("DB_NAME", "origins_bangladesh")

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "compilebreakers@gmail.com")
    SMTP_PASS = os.getenv("SMTP_PASS", "wngz bbfr mght hscq")
    SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")

    BASE_URL = os.getenv("BASE_URL", "https://origins-bangladesh.onrender.com")
