import datetime
import json
import secrets

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.generic.base import View

from hidrateapp.models import ACL, Bottle, Day, Glow, Installation, Location, Sip, User, UserHealthStats
from hidrateapp.util import parse_int_safe


def home(request):
    return HttpResponse('success {}'.format(request.method))


class APIException(Exception):
    def __init__(self, response, status=400):
        self.response = response
        self.status = status


class APIView(View):
    def setup_api(self, request, *args, **kwargs):
        pass

    def access_check(self, request, *args, **kwargs):
        application_id_matches = secrets.compare_digest(
            self.request.headers.get(settings.HIDRATE_APPLICATION_ID_HEADER, ''),
            settings.HIDRATE_APPLICATION_ID_VALUE,
        )
        rest_api_key_matches = secrets.compare_digest(
            self.request.headers.get(settings.HIDRATE_REST_API_KEY_HEADER, ''),
            settings.HIDRATE_REST_API_KEY_VALUE,
        )
        client_key_matches = secrets.compare_digest(
            self.request.headers.get(settings.HIDRATE_CLIENT_KEY_HEADER, ''),
            settings.HIDRATE_CLIENT_KEY_VALUE,
        )

        authorized = application_id_matches and (rest_api_key_matches or client_key_matches)

        if not authorized:
            raise APIException({'error': 'unauthorized'})

    def parse_json(self, data):
        try:
            if not data:
                return {}
            if len(data) > 10**7:
                raise ValueError()
            return json.loads(data, parse_int=parse_int_safe)
        except (ValueError, UnicodeDecodeError, json.decoder.JSONDecodeError):
            raise APIException({'code': 202, 'error': 'invalid json'})

    @property
    def acls(self):
        if self.request.hidrate_user is None:
            return ACL.objects.none()
        return self.request.hidrate_user.acls.all()

    def dispatch(self, request, *args, **kwargs):
        try:
            self.access_check(request, *args, **kwargs)
            self.data = self.parse_json(request.body)

            if '_method' in self.data and request.method.lower() != self.data['_method'].lower():
                request._method = request.method
                request.method = self.data['_method'].lower()
                setattr(request, self.data['_method'].upper(), self.data)
                del self.data['_method']

            self.setup_api(request, *args, **kwargs)
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            import traceback
            traceback.print_exc()
            return JsonResponse(e.response, status=e.status)


class LoginRequiredMixin:
    def access_check(self, request, *args, **kwargs):
        super().access_check(request, *args, **kwargs)

        if self.request.hidrate_user is None:
            raise APIException({'code': 206, 'error': 'login required'})


class UpdateObjectFieldsMixin:
    def update_object_fields(self, obj):
        for key, value in self.data.items():
            try:
                obj.update_value(key, value)
            except (AttributeError, KeyError):
                raise APIException({
                    'code': 202,
                    'error': f'Unknown field {key}',
                })
            except (ValueError, ObjectDoesNotExist):
                raise APIException({
                    'code': 202,
                    'error': f'Invalid type for {key}',
                })

        try:
            obj.save()
        except Exception:
            import traceback
            traceback.print_exc()
            raise APIException({
                'code': 202,
                'error': 'failed',
            })

        return obj


class SingleObjectMixin:
    object_class = None

    def get_object(self, *args, **kwargs):
        raise NotImplementedError()

    def setup_api(self, request, *args, **kwargs):
        self.object = self.get_object()


class BatchObjectMixin:
    object_class = None

    def get_objects(self, objects=None):
        raise NotImplementedError()


class AltersDataMixin:
    def update_other(self):
        pass


class GetObjectMixin(SingleObjectMixin):
    get_access_check = True

    def get_get_response(self, *args, **kwargs):
        return self.object.serialize_full()

    def get(self, *args, **kwargs):
        if (
            self.get_access_check and
            not self.object.acl.filter(user=self.request.hidrate_user, permission='read').exists()
        ):
            raise APIException({'code': 209, 'error': 'no permission'})
        return JsonResponse(self.get_get_response())


class CreateObjectMixin(AltersDataMixin, UpdateObjectFieldsMixin, SingleObjectMixin):
    def get_create_response(self, *args, **kwargs):
        return {
            'objectId': self.object.serialize_field('objectId'),
            'createdAt': self.object.serialize_field('createdAt'),
        }

    def get_object(self, obj=None):
        if obj is not None:
            return obj
        return self.object_class()

    def update_other(self):
        super().update_other()
        self.object.acl.set(self.acls.filter(permission__in=('read', 'write')))

    def post(self, *args, **kwargs):
        self.object = self.update_object_fields(self.object)
        self.update_other()
        return JsonResponse(self.get_create_response())


class UpdateObjectMixin(AltersDataMixin, UpdateObjectFieldsMixin, SingleObjectMixin):
    put_access_check = True

    def get_put_response(self, *args, **kwargs):
        return {
            'objectId': self.object.serialize_field('objectId'),
            'updatedAt': self.object.serialize_field('updatedAt'),
        }

    def put(self, *args, **kwargs):
        if (
            self.put_access_check and
            not self.object.acl.filter(user=self.request.hidrate_user, permission='write').exists()
        ):
            raise APIException({'code': 209, 'error': 'no permission'})
        self.object = self.update_object_fields(self.object)
        self.update_other()
        return JsonResponse(self.get_put_response())


class DeleteObjectMixin(AltersDataMixin, SingleObjectMixin):
    delete_access_check = True

    def get_delete_response(self, *args, **kwargs):
        return {}

    def delete(self, *args, **kwargs):
        if (
            self.delete_access_check and
            not self.object.acl.filter(user=self.request.hidrate_user, permission='write').exists()
        ):
            raise APIException({'code': 209, 'error': 'no permission'})
        self.object.delete()
        self.update_other()
        return JsonResponse(self.get_delete_response())


class ListObjectMixin(BatchObjectMixin):
    list_access_check = True

    def get_get_response(self, *args, **kwargs):
        results = []
        for obj in self.objects:
            results.append(obj.serialize_full())

        return {'results': results}

    def get(self, *args, **kwargs):
        if self.list_access_check and self.request.hidrate_user is not None:
            objects = self.object_class.objects.filter(acl__user=self.request.hidrate_user, acl__permission='read')
        else:
            objects = None

        self.objects = self.get_objects(objects)
        return JsonResponse(self.get_get_response())


class ObjectIDMixin:
    id_field = 'objectId'

    def setup(self, request, *args, **kwargs):
        self.id = kwargs.get('id')
        super().setup(request, *args, **kwargs)

    def get_object(self, obj=None):
        if obj is not None:
            return obj
        try:
            return self.object_class.objects.get(**{self.id_field: self.id})
        except ObjectDoesNotExist:
            raise APIException({
                'code': 202,
                'error': 'does not exist',
            })


class BatchObjectSimpleMixin:
    def get_objects(self, objects=None):
        if objects is not None:
            return objects
        return self.object_class.objects.all()


class BatchObjectFilterMixin:
    def filter_where(self, objects, where):
        if where is None:
            return objects

        where = self.parse_json(where)

        q = {}

        for key, value in where.items():
            if key not in self.object_class.full_fields:
                raise APIException({'code': 202, 'error': 'invalid where'})

            try:
                q[key] = self.object_class.unserialize_field(key, value)
            except (ValueError, ValidationError, ObjectDoesNotExist):
                raise APIException({'code': 202, 'error': 'invalid where'})

        return objects.filter(**q)

    def filter_order(self, objects, order):
        if order is None:
            return objects

        real_order = order[1:] if order.startswith('-') else order
        if real_order not in self.object_class.full_fields:
            raise APIException({'code': 202, 'error': 'invalid order'})
        return objects.order_by(order)

    def filter_limit(self, objects, limit):
        if limit is None:
            return objects

        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError()
        except ValueError:
            raise APIException({'code': 202, 'error': 'invalid limit'})
        else:
            return objects[:limit]

    def get_objects(self, objects=None):
        if objects is None:
            objects = self.object_class.objects.all()

        objects = self.filter_where(objects, self.filter.get('where'))
        objects = self.filter_order(objects, self.filter.get('order'))
        objects = self.filter_limit(objects, self.filter.get('limit'))

        return objects

    def setup_api(self, *args, **kwargs):
        self.filter = self.request.GET
        super().setup_api(*args, **kwargs)


class Config(APIView):
    def get(self, *args, **kwargs):
        return JsonResponse({
            'params': {
                'iOSLatestVersion': '2.1.7',
                'androidLatestVersion': '2.2.25',
                'firmwareUpdateFractionAndroid': 1,
                'downloadAppUrl': 'https://hidrate.page.link/friend',
                'androidPregnancySettings': False,
                'natalModifier': 1.25,
                'bottleVendors': {
                    'amazon': 'Amazon',
                    'hidrate': 'HidrateSpark.com',
                    'target': 'Target',
                    'apple': 'Apple',
                },
                'trophyShareUrl': 'https://hidratesparktrophies.com/trophy/',
                'trophySign': 'RANDOM',
                'iOSHideNFC': True,
                'androidNfcVersion': '135',
                'androidTumblerPlasticVisibility': False,
                'hidePro': True,
                'androidNfcEnabled': False,
            },
            'masterKeyOnly': {
                'iOSLatestVersion': False,
                'bottleVendors': False,
                'androidLatestVersion': False,
                'trophyShareUrl': False,
                'trophySign': False,
                'iOSHideNFC': False,
                'androidNfcVersion': False,
                'androidTumblerPlasticVisibility': False,
                'hidePro': False,
                'androidNfcEnabled': False,
            },
        })


class LoginView(GetObjectMixin, APIView):
    def get_object(self):
        try:
            return User.validate_password(self.data.get('username'), self.data.get('password'))
        except ValueError:
            raise APIException({
                'code': 101,
                'error': 'invalid username/password.',
            }, status=404)

    def get_get_response(self):
        resp = super().get_get_response()
        resp['sessionToken'] = self.request.hidrate_session.get_or_create_session_key()
        return resp

    def get(self, *args, **kwargs):
        self.request.hidrate_user = self.object
        return super().get(*args, **kwargs)


class LogoutView(LoginRequiredMixin, APIView):
    def post(self, *args, **kwargs):
        self.request.hidrate_session.set_expiry(-1)
        return JsonResponse({})


class SipMixin:
    def update_other(self):
        super().update_other()
        self.object.day.update_volume_stats()
        for stat in self.object.user.userhealthstats_set.iterator():
            stat.update_volume_stats()


class Classes:
    class InstallationView(CreateObjectMixin, APIView):
        object_class = Installation

    class DetailInstallationView(ObjectIDMixin, GetObjectMixin, UpdateObjectMixin, APIView):
        get_acess_check = False
        put_access_check = False
        object_class = Installation

    class UserView(CreateObjectMixin, APIView):
        object_class = User

        def update_other(self):
            self.request.hidrate_user = self.object
            ACL.objects.bulk_create(
                [ACL(user=self.request.hidrate_user, permission=perm) for perm in ('read', 'write')],
                ignore_conflicts=True,
            )

            userhealth = UserHealthStats.objects.create(user=self.object)
            userhealth.acl.set(self.acls.filter(permission__in=('read', 'write')))

            super().update_other()

        def update_object_fields(self, obj):
            if 'password' not in self.data:
                raise APIException({'code': 202, 'error': 'no password'})
            obj.set_password(self.data.pop('password'))

            return super().update_object_fields(obj)

        def get_create_response(self):
            resp = super().get_create_response()
            resp['sessionToken'] = self.request.hidrate_session.get_or_create_session_key()
            return resp

        def get(self, *args, **kwargs):
            return JsonResponse({
                'results': [],
            })

    class DetailUserView(LoginRequiredMixin, ObjectIDMixin, GetObjectMixin, UpdateObjectMixin, APIView):
        object_class = User

        def update_other(self):
            super().update_other()

            recommended = self.object.compute_recommended_goal()
            (
                Day.objects
                .filter(
                    user=self.object,
                    acl__user=self.request.hidrate_user,
                    acl__permission='write',
                    date__gte=timezone.now() - timezone.timedelta(hours=12),
                ).
                update(
                    recommendedGoal=recommended,
                    goal=self.object.goal or recommended,
                )
            )

        def get_get_response(self):
            resp = super().get_get_response()
            resp['sessionToken'] = self.request.hidrate_session.get_or_create_session_key()
            return resp

    class UserHealthStats(LoginRequiredMixin, BatchObjectFilterMixin, ListObjectMixin, APIView):
        object_class = UserHealthStats

        def filter_where(self, objects, where):
            if where is None:
                return objects

            where = self.parse_json(where)

            try:
                objects = objects.filter(user_id=where['user_id'])
            except KeyError:
                pass
            except (ValueError, ValidationError):
                raise APIException({'code': 202, 'error': 'invalid where'})

            return objects

    class DetailUserHealthStats(LoginRequiredMixin, ObjectIDMixin, UpdateObjectMixin, APIView):
        object_class = UserHealthStats

        def update_object_fields(self, obj):
            obj.statDate = timezone.now()
            return super().update_object_fields(obj)

    class SipView(SipMixin, LoginRequiredMixin, BatchObjectFilterMixin, CreateObjectMixin, ListObjectMixin, APIView):
        object_class = Sip

        def get_create_response(self, *args, **kwargs):
            resp = super().get_create_response(*args, **kwargs)
            resp['time'] = self.object.serialize_field('time')
            return resp

    class DetailSipView(
        SipMixin,
        LoginRequiredMixin,
        ObjectIDMixin,
        GetObjectMixin,
        UpdateObjectMixin,
        DeleteObjectMixin,
        APIView,
    ):
        object_class = Sip

        def get_put_response(self, *args, **kwargs):
            resp = super().get_put_response(*args, **kwargs)
            resp['time'] = self.object.serialize_field('time')
            return resp

    class BottleView(LoginRequiredMixin, BatchObjectFilterMixin, CreateObjectMixin, ListObjectMixin, APIView):
        object_class = Bottle

        def get_create_response(self, *args, **kwargs):
            resp = super().get_create_response(*args, **kwargs)
            for field in ('lastSynced', 'shouldUpdate'):
                resp[field] = self.object.serialize_field(field)
            return resp

    class DetailBottleView(
        LoginRequiredMixin,
        ObjectIDMixin,
        GetObjectMixin,
        UpdateObjectMixin,
        DeleteObjectMixin,
        APIView,
    ):
        object_class = Bottle

        def get_put_response(self, *args, **kwargs):
            resp = super().get_put_response(*args, **kwargs)
            resp['lastSynced'] = self.object.serialize_field('lastSynced')
            return resp

    class LocationView(LoginRequiredMixin, CreateObjectMixin, APIView):
        object_class = Location

    class DetailLocationView(
        LoginRequiredMixin,
        ObjectIDMixin,
        GetObjectMixin,
        UpdateObjectMixin,
        DeleteObjectMixin,
        APIView,
    ):
        object_class = Location

    class DayView(LoginRequiredMixin, BatchObjectFilterMixin, ListObjectMixin, APIView):
        object_class = Day

        def get(self, *args, **kwargs):
            today = datetime.date.today()
            weekday = today.weekday() or 7
            week_start = today - datetime.timedelta(days=weekday)
            batch_days = []

            recommended = self.request.hidrate_user.compute_recommended_goal()

            for i in range(max(weekday + 2, 7)):
                batch_days.append(
                    Day(
                        user=self.request.hidrate_user,
                        date=week_start + datetime.timedelta(days=i),
                        recommendedGoal=recommended,
                        goal=self.request.hidrate_user.goal or recommended,
                    ),
                )
            Day.objects.bulk_create(batch_days, ignore_conflicts=True)

            for day in (
                Day.objects
                .filter(user=self.request.hidrate_user)
                .exclude(acl__user=self.request.hidrate_user)
                .iterator()
            ):
                day.acl.add(*self.acls.filter(permission__in=('read', 'write')))

            return super().get(*args, **kwargs)

    class DetailDayView(
        LoginRequiredMixin,
        ObjectIDMixin,
        GetObjectMixin,
        UpdateObjectMixin,
        DeleteObjectMixin,
        APIView,
    ):
        object_class = Day

        def get_put_response(self, *args, **kwargs):
            resp = super().get_put_response(*args, **kwargs)
            for field in ('recommendedGoal', 'goal', 'totalBottleAmount'):
                resp[field] = self.object.serialize_field(field)
            return resp


class Functions:
    class UserExists(APIView):
        def post(self, request, *args, **kwargs):
            try:
                email = request.GET['email']
            except KeyError:
                return JsonResponse({})
            else:
                return JsonResponse({
                    'result': {
                        'exists': User.objects.filter(email=email).exists(),
                        'emailverified': False,
                    },
                })

    class CanAddBottle(APIView):
        def post(self, request, *args, **kwargs):
            return JsonResponse({
                'result': {
                    'canAdd': True,
                    'bottleData': {},
                },
            })

    class DeleteGlow(LoginRequiredMixin, ObjectIDMixin, DeleteObjectMixin, APIView):
        object_class = Glow
        id_field = 'id'

        def setup(self, request, *args, **kwargs):
            super().setup(request, *args, **kwargs)
            self.id = self.request.GET.get('glowId')
            if self.id is None:
                raise APIException({'code': 202, 'error': 'glowId required'})

        def get_delete_response(self, *args, **kwargs):
            return {
                'result': 'Glow deleted successfully',
            }

        def post(self, *args, **kwargs):
            return super().delete(*args, **kwargs)

    class CreateGlow(LoginRequiredMixin, CreateObjectMixin, APIView):
        object_class = Glow

        def get_create_response(self, *args, **kwargs):
            return {
                'result': {
                    'message': 'Glow saved successfully',
                    'glowId': self.object.serialize_field('id'),
                },
            }

        def get_object(self, obj=None):
            if obj is None and 'id' in self.data:
                try:
                    obj = self.object_class.objects.get(id=self.data['id'])
                except (ValueError, ValidationError, ObjectDoesNotExist):
                    pass
                del self.data['id']

            return super().get_object(obj)

        def setup_api(self, request, *args, **kwargs):
            if 'glow' not in self.data:
                raise APIException({'code': 202, 'error': 'missing glow'})
            self.data = self.data['glow']

            super().setup_api(request, *args, **kwargs)

    class ListGlow(LoginRequiredMixin, BatchObjectSimpleMixin, ListObjectMixin, APIView):
        object_class = Glow

        def get_get_response(self, *args, **kwargs):
            return {
                'result': super().get_get_response(*args, **kwargs)['results'],
            }

        def post(self, request, *args, **kwargs):
            return super().get(request, *args, **kwargs)

    class CalculateDayTotal(LoginRequiredMixin, ObjectIDMixin, GetObjectMixin, APIView):
        object_class = Day
        id_field = 'objectId'

        def setup(self, request, *args, **kwargs):
            super().setup(request, *args, **kwargs)
            self.id = self.request.GET.get('dayId')
            if self.id is None:
                raise APIException({'code': 202, 'error': 'dayId required'})

        def get_get_response(self, *args, **kwargs):
            return {
                'dayTotal': self.object.serialize_field('totalAmount'),
                'dayId': self.object.serialize_field('objectId'),
            }

        def post(self, request, *args, **kwargs):
            return super().get(request, *args, **kwargs)


def empty(request, path=None):
    return JsonResponse({
        'results': [],
        'result': [],
    }, status=202)
