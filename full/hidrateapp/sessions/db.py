from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore


class HidrateSessionStore(SessionStore):
    @classmethod
    def get_model_class(cls):
        from hidrateapp.sessions.models import HidrateSession
        return HidrateSession

    def get_session_cookie_age(self):
        return settings.HIDRATE_SESSION_AGE

    def get_or_create_session_key(self):
        if self.session_key is None:
            self.create()
        return self.session_key
