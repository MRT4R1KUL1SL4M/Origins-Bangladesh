import os

class Config:
    # App Security
    SECRET_KEY = os.getenv("SECRET_KEY", "origins-bd-secret-12345")

    # Database (TiDB Cloud Connection)
    DB_HOST = os.getenv("DB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com")
    DB_USER = os.getenv("DB_USER", "2cPo7b5N2rLWuv9.root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "P6S0HBGaSQY1gw74")
    DB_NAME = os.getenv("DB_NAME", "origins_bangladesh")
    
    # TiDB er jonno SSL on kora dorkar (cloud db tai)
    DB_SSL_DISABLED = os.getenv("DB_SSL_DISABLED", "false")

    # Email (Gmail SMTP)
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "compilebreakers@gmail.com")
    SMTP_PASS = os.getenv("SMTP_PASS", "wngz bbfr mght hscq")
    SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@example.com")
    
    # Live URL (Vercel ba Render-er URL dibe ekhane)
    BASE_URL = os.getenv("BASE_URL", "https://origins-bangladesh.vercel.app")
