from django.apps import AppConfig
from pathlib import Path
import os

import firebase_admin
from firebase_admin import credentials as fb_credentials
from athena_logging import get_logger

logger = get_logger(__name__)

class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "Athena API"

    def ready(self) -> None:
        # Initialize Firebase Admin if available and not already initialized
        if firebase_admin is None or fb_credentials is None:
            return

        if firebase_admin._apps:  # already initialized
            return

        # Resolve credentials path from environment
        cred_path = os.getenv("FIREBASE_CREDENTIALS")

        try:
            # 1) Service account JSON via explicit env var path
            if cred_path and Path(cred_path).exists():
                credentials = fb_credentials.Certificate(cred_path)
                firebase_admin.initialize_app(credentials)
                logger.info(f"Initialized Firebase Admin with service account JSON at {cred_path}")
                return

            # 2) Application Default Credentials (ADC), e.g., GOOGLE_APPLICATION_CREDENTIALS, GCE/GKE metadata
            try:
                credentials = fb_credentials.ApplicationDefault()
                firebase_admin.initialize_app(credentials, options={"projectId": "athena-5b322"})
                logger.info("Initialized Firebase Admin with Application Default Credentials")
                return
            except Exception as adc_error:
                logger.warning(f"Application Default Credentials not available: {adc_error}")

            # 3) Let SDK attempt default discovery without explicit credentials
            firebase_admin.initialize_app()
            logger.info("Initialized Firebase Admin using default environment configuration")
        except Exception:
            logger.exception(
                "Failed to initialize Firebase Admin. Set FIREBASE_CREDENTIALS or "
                "GOOGLE_APPLICATION_CREDENTIALS to a valid service account JSON path."
            )