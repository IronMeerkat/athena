"""
Django settings for the Athena DRF gateway.

This settings module is intentionally simple.  It enables the core Django
functionality, Django REST Framework, Channels for WebSocket support and
Celery for background tasks.  It also includes a placeholder for Firebase
configuration.  You should update the secret key and database
configuration for your environment.  Environment variables defined in a
.env file (if present) can override these defaults via ``python-dotenv``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
import urllib.parse as urlparse
from dotenv import load_dotenv


# Load variables from .env file if present.  This allows you to provide
# secret keys, database URLs and other configuration without modifying
# this file directly.  See ``.env.example`` for guidance.


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

SECRET_KEY: str = os.getenv("DJANGO_SECRET_KEY", "replace-me-please")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = os.getenv("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS: List[str] = os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    'rest_framework_simplejwt',
    "corsheaders",
    "channels",
    # Local apps
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# URL configuration module
ROOT_URLCONF = "athena_drf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# WSGI application
WSGI_APPLICATION = "athena_drf.wsgi.application"

# ASGI application for Channels
ASGI_APPLICATION = "athena_drf.asgi.application"

# Database configuration: use Postgres if DATABASE_URL is provided,
# otherwise fall back to SQLite for development.
DATABASE_URL = os.getenv("DATABASE_URL")


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SIMPLE_JWT = {
    "ALGORITHM": "HS512"
}
# Internationalization
LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/New_York"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework basic configuration.  You can further
# customize authentication classes, throttling, pagination, etc.
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        'athena_drf.firebase_stuff.FirebaseAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # "rest_framework.authentication.SessionAuthentication",
        # "rest_framework.authentication.BasicAuthentication",
    ],
}

# CORS settings: allow all origins by default for development.  In
# production restrict these to known client origins.
CORS_ALLOW_ALL_ORIGINS = True

AUTH_USER_MODEL = 'api.User'
# Channels configuration: use Redis as the channel layer backend.  This
# allows WebSocket consumers to communicate across multiple worker
# processes.  The host/port mirror the values defined in docker-compose.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST", "redis"), int(os.getenv("REDIS_PORT", 6379)))],
        },
    },
}

# Celery configuration.  The broker points to RabbitMQ for message queuing,
# while the result backend uses RPC.  This file is read by Celery when creating
# the app in ``celery.py``.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://admin:admin@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "rpc://")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
