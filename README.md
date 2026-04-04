# Origins Bangladesh (Flask + MySQL)

## Setup

1. Create DB and run schema + seed:

```sql
CREATE DATABASE origins_bangladesh CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE origins_bangladesh;
SOURCE database/schema.sql;
SOURCE database/seed.sql;
```

2. Install deps:

```bash
pip install -r requirements.txt
```

3. Create `.env` (example):

```bash
SECRET_KEY=change-me
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=YOUR_DB_PASS
DB_NAME=origins_bangladesh

# Gmail SMTP (use an App Password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourgmail@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM="Origins Bangladesh <yourgmail@gmail.com>"

# Optional (recommended in production)
BASE_URL=https://yourdomain.com/
```

> For Gmail, enable 2FA and create an **App Password**. Use that as `SMTP_PASS`.

4. Run:

```bash
python app.py
```

## Auth (New)

- Login: email → OTP + magic link (superadmin/admin/seller/buyer supported)
- Register: buyer default, seller via `Register?role=seller` CTA
- Forgot password: email → OTP + reset link
