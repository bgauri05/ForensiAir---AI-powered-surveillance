import os

SECRET_KEY = os.getenv("SECRET_KEY", "forensiair_secret_key_jwt_2026")
ALGORITHM = "HS256"

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

INSPECTOR_USERNAME = os.getenv("INSPECTOR_USERNAME", "inspector")
INSPECTOR_PASSWORD = os.getenv("INSPECTOR_PASSWORD", "inspector123")
