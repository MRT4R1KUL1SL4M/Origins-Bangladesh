import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "1046")
    DB_NAME = os.getenv("DB_NAME", "origins_bangladesh")


    # Email (Gmail SMTP)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "compilebreakers@gmail.com")
    SMTP_PASS = os.getenv("SMTP_PASS", "wngz bbfr mght hscq")
    SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")
    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")  # e.g. https://yourdomain.com/
