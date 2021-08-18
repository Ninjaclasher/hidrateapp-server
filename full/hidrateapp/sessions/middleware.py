from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted


from hidrateapp.models import User
from hidrateapp.sessions.db import HidrateSessionStore


class HidrateSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_key = request.headers.get(settings.HIDRATE_SESSION_HEADER)
        request.hidrate_session = HidrateSessionStore(session_key)

        try:
            request.hidrate_user = User.objects.get(objectId=request.hidrate_session.get('userId'))
        except User.DoesNotExist:
            request.hidrate_user = None

        response = self.get_response(request)

        if request.hidrate_user is not None and request.hidrate_session.get('userId') != request.hidrate_user.objectId:
            request.hidrate_session['userId'] = request.hidrate_user.objectId

        try:
            modified = request.hidrate_session.modified
            empty = request.hidrate_session.is_empty()
        except AttributeError:
            return response

        if not empty and (modified or settings.SESSION_SAVE_EVERY_REQUEST) and response.status_code != 500:
            try:
                request.hidrate_session.save()
            except UpdateError:
                raise SessionInterrupted(
                    "The request's session was deleted before the "
                    "request completed. The user may have logged "
                    "out in a concurrent request, for example.",
                )

        return response
