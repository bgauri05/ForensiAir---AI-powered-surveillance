import os

# QC FIX (2026-08): same category of issue as the Postgres password fix --
# these used to have hardcoded fallback credentials (admin/admin123,
# inspector/inspector123) that are now sitting in a *public* GitHub repo's
# history. A dev-convenience default is genuinely useful locally, so this
# keeps one, but only for local/dev use, and only when APP_ENV isn't set to
# "production" -- set APP_ENV=production (and the real credentials below)
# for any real deployment.
APP_ENV = os.getenv("APP_ENV", "development")

SECRET_KEY = os.getenv("SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
INSPECTOR_USERNAME = os.getenv("INSPECTOR_USERNAME")
INSPECTOR_PASSWORD = os.getenv("INSPECTOR_PASSWORD")

_missing = [
    name for name, val in [
        ("SECRET_KEY", SECRET_KEY), ("ADMIN_USERNAME", ADMIN_USERNAME),
        ("ADMIN_PASSWORD", ADMIN_PASSWORD), ("INSPECTOR_USERNAME", INSPECTOR_USERNAME),
        ("INSPECTOR_PASSWORD", INSPECTOR_PASSWORD)
    ] if not val
]

if _missing:
    if APP_ENV == "production":
        raise RuntimeError(
            f"Missing required environment variable(s) in production: {', '.join(_missing)}."
        )
    print(
        f"[config] WARNING: {', '.join(_missing)} not set -- using local dev-only fallback "
        "credentials (admin/admin123, inspector/inspector123). Do NOT deploy like this."
    )
    ALGORITHM = "HS256"
    SECRET_KEY = SECRET_KEY or "forensiair_secret_key_jwt_2026"
    ADMIN_USERNAME = ADMIN_USERNAME or "admin"
    ADMIN_PASSWORD = ADMIN_PASSWORD or "admin123"
    INSPECTOR_USERNAME = INSPECTOR_USERNAME or "inspector"
    INSPECTOR_PASSWORD = INSPECTOR_PASSWORD or "inspector123"
else:
    ALGORITHM = "HS256"
