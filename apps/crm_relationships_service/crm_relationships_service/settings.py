import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "crm-relationships-service-dev-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,crm-relationships-service",
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "apps.crm",
    "apps.health",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "crm_relationships_service.urls"
TEMPLATES = []
WSGI_APPLICATION = "crm_relationships_service.wsgi.application"

DATABASES = {
    "default": (
        {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test.sqlite3",
        }
        if "test" in sys.argv
        else {
            "ENGINE": os.environ.get(
                "DB_ENGINE",
                "django.db.backends.postgresql",
            ),
            "NAME": os.environ.get("DB_NAME", "crm_relationships_service"),
            "USER": os.environ.get("DB_USER", "crm"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "crm"),
            "HOST": os.environ.get("DB_HOST", "crm-db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    )
}

KAFKA_BOOTSTRAP_SERVERS = [
    server.strip()
    for server in os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092").split(",")
    if server.strip()
]
DEAL_STATUS_CHANGED_TOPIC = os.environ.get(
    "DEAL_STATUS_CHANGED_TOPIC",
    "deal.status_changed",
)
KAFKA_CONSUMER_ENABLED = (
    os.environ.get("KAFKA_CONSUMER_ENABLED", "true").lower() == "true"
)
KAFKA_CONSUMER_GROUP = os.environ.get(
    "KAFKA_CONSUMER_GROUP",
    "crm-relationships-service",
)
KAFKA_CONSUMER_POLL_TIMEOUT_MS = int(
    os.environ.get("KAFKA_CONSUMER_POLL_TIMEOUT_MS", "1000"),
)
KAFKA_CONSUMER_MAX_RETRIES = int(
    os.environ.get("KAFKA_CONSUMER_MAX_RETRIES", "3"),
)
KAFKA_CONSUMER_RETRY_DELAY_SECONDS = float(
    os.environ.get("KAFKA_CONSUMER_RETRY_DELAY_SECONDS", "1"),
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "loggers": {
        "kafka": {
            "level": "WARNING",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}
