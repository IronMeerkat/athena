from django.apps import AppConfig
from django.conf import settings
from pathlib import Path
import os

import firebase_admin
from firebase_admin import credentials as fb_credentials


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

        # Prefer explicit env var
        cred_path = os.getenv("FIREBASE_CREDENTIALS")
        if not cred_path:
            # Fallback: try to find a single JSON key in the athena_drf directory
            drf_dir = Path(settings.BASE_DIR) / "athena_drf"
            json_keys = list(drf_dir.glob("*.json"))
            if len(json_keys) == 1:
                cred_path = str(json_keys[0])

        if cred_path and Path(cred_path).exists():
            try:
                credentials = fb_credentials.Certificate(cred_path)
                firebase_admin.initialize_app(credentials)
            except Exception:
                # Silently continue; API views will raise on verification if misconfigured
                pass
        else:
            # No credentials found; skip initialization
            pass