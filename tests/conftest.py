import os

os.environ.setdefault("FIREBASE_CREDENTIALS", "{}")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("SMTP_HOST", "smtp.gmail.com")
os.environ.setdefault("SMTP_PORT", "587")
os.environ.setdefault("SMTP_USER", "test@example.com")
os.environ.setdefault("SMTP_PASSWORD", "test-password")
os.environ.setdefault("SMTP_FROM", "test@example.com")