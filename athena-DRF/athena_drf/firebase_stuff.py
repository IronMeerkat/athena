from rest_framework.authentication import BaseAuthentication
from firebase_admin import auth as fb_auth
from django.contrib.auth import get_user_model

class FirebaseAuthentication(BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        if not token or fb_auth is None:
            return None
        try:
            decoded = fb_auth.verify_id_token(token, check_revoked=True)
        except Exception:
            return None
        uid = decoded.get("uid")
        if not uid:
            return None
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username=uid,
            defaults={"email": decoded.get("email", "")},
        )
        return (user, None)