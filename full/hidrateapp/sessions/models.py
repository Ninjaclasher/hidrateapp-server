from django.contrib.sessions.base_session import AbstractBaseSession, BaseSessionManager


class HidrateSessionManager(BaseSessionManager):
    use_in_migrations = True


class HidrateSession(AbstractBaseSession):
    objects = HidrateSessionManager()

    @classmethod
    def get_session_store_class(cls):
        from hidrateapp.sessions.db import HidrateSessionStore
        return HidrateSessionStore

    class Meta(AbstractBaseSession.Meta):
        db_table = 'hidrate_session'
