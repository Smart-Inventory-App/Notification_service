import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_notification.db")
os.environ.setdefault("FIREBASE_CREDENTIALS", "{}")
os.environ.setdefault("JWT_SECRET", "test-secret")
