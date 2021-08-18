import datetime
import secrets
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone

from hidrateapp.sessions.models import HidrateSession  # noqa: F401
from hidrateapp.util import sanitize_isodate, unsanitize_isodate


def object_id_gen():
    return secrets.token_urlsafe(16)


class ObjectIDAutoField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(**{
            'max_length': 32,
            'default': object_id_gen,
            'primary_key': True,
            'editable': False,
        })
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs['max_length']
        del kwargs['default']
        del kwargs['primary_key']
        del kwargs['editable']
        return name, path, args, kwargs


class SerializableMixin:
    full_fields = ()
    fk_fields = ()
    updateable_fields = ()
    type_name = None
    class_name = None

    def serialize_field(self, field):
        clz = self.__class__._meta.get_field(field).__class__
        obj = getattr(self, field)
        if obj is None:
            return obj
        elif clz == models.ForeignKey:
            model = self.__class__._meta.get_field(field).remote_field.model
            return model.serialize_fk(obj)
        elif callable(getattr(clz, 'serialize_fk', None)):
            return clz.serialize_fk(obj)
        elif callable(getattr(obj, 'isoformat', None)):
            if clz == models.DateField:
                return obj.isoformat()
            elif clz == models.DateTimeField:
                return unsanitize_isodate(obj.isoformat(timespec='microseconds'))
            else:
                raise ValueError('Unknown type {}'.format(str(clz)))
        else:
            return obj

    @classmethod
    def unserialize_field(cls, field, value):
        clz = cls._meta.get_field(field).__class__
        if clz == models.ForeignKey:
            model = cls._meta.get_field(field).remote_field.model
            return model.unserialize_fk(value)
        elif callable(getattr(clz, 'unserialize_fk', None)):
            return clz.unserialize_fk(value)
        elif callable(getattr(clz, 'isoformat', None)):
            if isinstance(clz, models.DateField):
                return datetime.date.fromisoformat(sanitize_isodate(value))
            elif isinstance(clz, models.DateTimeField):
                return datetime.datetime.fromisoformat(sanitize_isodate(value))
            else:
                raise ValueError('Unknown type {}'.format(str(clz)))
        return value

    def serialize_full(self):
        resp = {}
        for field in self.full_fields:
            value = self.serialize_field(field)
            if value is None:
                continue
            resp[field] = value
        return resp

    @classmethod
    def serialize_fk(cls, data):
        resp = {}
        for field in cls.fk_fields:
            resp[field] = getattr(data, field)

        if cls.type_name is not None:
            resp['__type'] = cls.type_name
        if cls.class_name is not None:
            resp['className'] = cls.class_name
        return resp

    @classmethod
    def unserialize_fk(cls, data):
        if cls.type_name != data.pop('__type', None):
            raise ValueError()

        if cls.class_name != data.pop('className', None):
            raise ValueError()

        if set(cls.fk_fields) != set(data.keys()):
            raise ValueError()

        return cls.objects.get(**data)

    def update_value(self, key, value):
        if getattr(self, key, None) == value:
            return
        if key not in self.updateable_fields:
            raise AttributeError()

        setattr(self, key, self.unserialize_field(key, value))


class DateTimeField(SerializableMixin, models.DateTimeField):
    def serialize_full(self):
        raise NotImplementedError()

    @classmethod
    def serialize_fk(cls, data):
        return {
            '__type': 'Date',
            'iso': unsanitize_isodate(data.isoformat(timespec='microseconds')),
        }

    @classmethod
    def unserialize_fk(cls, data):
        return datetime.datetime.fromisoformat(sanitize_isodate(data['iso']))


class ACL(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='acls')
    permission = models.CharField(
        max_length=16,
        choices=(
            ('read', 'read'),
            ('write', 'write'),
        ),
    )

    class Meta:
        unique_together = ('user', 'permission')


class Bottle(SerializableMixin, models.Model):
    full_fields = (
        'objectId',
        'lastSynced',
        'batteryLevel',
        'capacity',
        'firmwareBootloaderVersion',
        'firmwareMinorVersion',
        'name',
        'serialNumber',
        'user',
        'shouldUpdate',
        'createdAt',
        'updatedAt',
        'description',
        'location',
    )
    fk_fields = (
        'objectId',
    )
    updateable_fields = (
        'batteryLevel',
        'capacity',
        'firmwareBootloaderVersion',
        'firmwareMinorVersion',
        'name',
        'serialNumber',
        'user',
        'should_update'
        'description',
        'location',
        'lastSynced',
    )
    type_name = 'Pointer'
    class_name = 'Bottle'

    objectId = ObjectIDAutoField()
    lastSynced = DateTimeField(auto_now=True)
    batteryLevel = models.IntegerField(default=0)
    capacity = models.IntegerField(default=0)
    firmwareBootloaderVersion = models.IntegerField(default=0)
    firmwareMinorVersion = models.IntegerField(default=0)
    name = models.CharField(max_length=128)
    serialNumber = models.CharField(max_length=128)
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    shouldUpdate = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    description = models.JSONField(default=dict)
    location = models.JSONField(null=True, default=None)

    acl = models.ManyToManyField('ACL')


class User(SerializableMixin, models.Model):
    full_fields = (
        'objectId',
        'birthday',
        'wakeUp',
        'goToSleep',
        'sipGlow',
        'gender',
        'weight',
        'timeZone',
        'fluidInMetric',
        'elevationInMetric',
        'heightInMetric',
        'lightNotificationCount',
        'degreesInMetric',
        'appNotificationCount',
        'name',
        'breastfeeding',
        'weightInMetric',
        'pushNotificationCount',
        'spam',
        'email',
        'activityLevel',
        'username',
        'height',
        'createdAt',
        'updatedAt',
        'agreedToTOS',
        'suppressedNotificationTypes',
        'bottleVendors',
        'fitbitUserId',
        'goal',
        'lightType',
        'pushNotificationAlways',
    )
    fk_fields = (
        'objectId',
    )
    updateable_fields = (
        'birthday',
        'wakeUp',
        'goToSleep',
        'sipGlow',
        'gender',
        'weight',
        'timeZone',
        'fluidInMetric',
        'elevationInMetric',
        'heightInMetric',
        'lightNotificationCount',
        'degreesInMetric',
        'appNotificationCount',
        'name',
        'breastfeeding',
        'weightInMetric',
        'pushNotificationCount',
        'spam',
        'email',
        'activityLevel',
        'username',
        'height',
        'agreedToTOS',
        'suppressedNotificationTypes',
        'bottleVendors',
        'fitbitUserId',
        'goal',
        'lightType',
        'pushNotificationAlways',
    )
    type_name = 'Pointer'
    class_name = '_User'

    objectId = ObjectIDAutoField()
    birthday = DateTimeField(null=True)
    wakeUp = DateTimeField(null=True)
    goToSleep = DateTimeField(null=True)
    sipGlow = models.BooleanField()
    gender = models.CharField(max_length=128)
    weight = models.FloatField()
    timeZone = models.CharField(max_length=128)
    fluidInMetric = models.BooleanField()
    elevationInMetric = models.BooleanField()
    heightInMetric = models.BooleanField()
    lightNotificationCount = models.IntegerField()
    degreesInMetric = models.BooleanField()
    appNotificationCount = models.IntegerField()
    name = models.CharField(max_length=128)
    breastfeeding = models.BooleanField(default=False)
    weightInMetric = models.BooleanField()
    pushNotificationCount = models.IntegerField()
    spam = models.BooleanField(default=False)
    email = models.EmailField(unique=True)
    activityLevel = models.PositiveSmallIntegerField()
    username = models.CharField(max_length=128, unique=True)
    height = models.FloatField()
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    agreedToTOS = models.BooleanField(default=False)
    suppressedNotificationTypes = models.JSONField(default=list)
    bottleVendors = models.JSONField(default=dict)
    fitbitUserId = models.CharField(max_length=128)
    goal = models.FloatField(null=True)
    lightType = models.IntegerField(default=0)
    pushNotificationAlways = models.BooleanField(default=False)
    password = models.CharField(max_length=1024)

    acl = models.ManyToManyField('ACL', related_name='+')

    def compute_recommended_goal(self):
        return 2000

    def set_password(self, password):
        self.password = make_password(password)

    @classmethod
    def validate_password(cls, username, password):
        if not username or not password:
            raise ValueError('invalid')
        try:
            user = User.objects.get(username=username)
        except cls.DoesNotExist:
            raise ValueError('invalid')
        if not check_password(password, user.password):
            raise ValueError('invalid')
        return user


class UserHealthStats(SerializableMixin, models.Model):
    full_fields = (
        'objectId',
        'user',
        'recentTotal',
        'recentGoal',
        'bottlesSaved',
        'createdAt',
        'updatedAt',
        'average',
        'goalMetCount',
        'statDate',
        'volume',
        'streak',
    )
    fk_object_fields = (
        'objectId',
    )
    updateable_fields = (
        'streak',
    )
    type_name = 'Pointer'
    class_name = 'UserHealthStats'

    def serialize_full(self):
        resp = super().serialize_full()
        resp['user_id'] = self.user.objectId
        return resp

    def update_volume_stats(self, commit=True):
        self.volume = self.user.sip_set.aggregate(s=Sum('amount'))['s'] or 0
        self.goalMetCount = self.user.day_set.filter(totalAmount__gte=F('goal')).count()
        if commit:
            self.save()

    objectId = ObjectIDAutoField()
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    recentTotal = models.FloatField(default=0)
    recentGoal = models.FloatField(default=0)
    bottlesSaved = models.IntegerField(default=0)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    average = models.FloatField(default=0)
    goalMetCount = models.IntegerField(default=0)
    statDate = DateTimeField(auto_now_add=True)
    volume = models.FloatField(default=0)
    streak = models.IntegerField(default=0)

    acl = models.ManyToManyField('ACL')


class Day(SerializableMixin, models.Model):
    full_fields = (
        'objectId',
        'user',
        'date',
        'totalAmount',
        'totalBottleAmount',
        'location',
        'isLocationUsed',
        'recommendedGoal',
        'goal',
        'createdAt',
        'updatedAt',
        'altitude',
        'humidity',
        'rank',
        'steps',
    )
    fk_fields = (
        'objectId',
    )
    updateable_fields = (
        'user',
        'date',
        'totalAmount',
        'totalBottleAmount',
        'location',
        'isLocationUsed',
        'recommendedGoal',
        'goal',
        'altitude',
        'humidity',
        'rank',
        'steps',
    )
    type_name = 'Pointer'
    class_name = 'Day'

    def serialize_full(self):
        resp = super().serialize_full()
        resp['locationUsed'] = self.serialize_field('isLocationUsed')
        return resp

    def update_volume_stats(self, commit=True):
        self.totalAmount = self.sip_set.aggregate(s=Sum('amount'))['s'] or 0
        self.totalBottleAmount = (
            self.sip_set
            .filter(bottleSerialNumber__isnull=False)
            .aggregate(s=Sum('amount'))['s']
        ) or 0
        if commit:
            self.save()

    objectId = ObjectIDAutoField()
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    date = models.DateField()
    totalAmount = models.IntegerField(default=0)
    totalBottleAmount = models.IntegerField(default=0)
    location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True)
    isLocationUsed = models.BooleanField(default=False)
    recommendedGoal = models.FloatField(default=0)
    goal = models.FloatField(null=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    altitude = models.FloatField(null=True)
    humidity = models.FloatField(null=True)
    rank = models.IntegerField(null=True)
    steps = models.IntegerField(null=True)

    acl = models.ManyToManyField('ACL')

    class Meta:
        unique_together = ('user', 'date')


class Location(SerializableMixin, models.Model):
    full_fields = (
        'objectId',
        'altitude',
        'point',
        'user',
    )
    fk_fields = (
        'objectId',
    )
    updateable_fields = (
        'altitude',
        'point',
        'user',
    )
    type_name = 'Pointer'
    class_name = 'Location'

    objectId = ObjectIDAutoField()
    altitude = models.FloatField()
    point = models.JSONField()
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    acl = models.ManyToManyField('ACL')


class Sip(SerializableMixin, models.Model):
    full_fields = (
        'objectId',
        'time',
        'amount',
        'bottleSerialNumber',
        'day',
        'max',
        'min',
        'start',
        'stop',
        'user',
        'createdAt',
        'updatedAt',
    )
    fk_object_fields = (
        'objectId',
    )
    updateable_fields = (
        'time',
        'amount',
        'bottleSerialNumber',
        'day',
        'max',
        'min',
        'start',
        'stop',
        'user',
    )
    type_name = 'Pointer'
    class_name = 'Sip'

    objectId = ObjectIDAutoField()
    time = DateTimeField(default=timezone.now)
    amount = models.IntegerField(default=0)
    bottleSerialNumber = models.CharField(max_length=128)
    day = models.ForeignKey('Day', on_delete=models.CASCADE)
    max = models.IntegerField(default=0)
    min = models.IntegerField(default=0)
    start = models.IntegerField(default=0)
    stop = models.IntegerField(default=0)
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    acl = models.ManyToManyField('ACL')


class Glow(SerializableMixin, models.Model):
    full_fields = (
        'name',
        'content',
        'id',
    )
    fk_object_fields = (
        'id',
    )
    updateable_fields = (
        'name',
        'content',
        'user',
    )
    type_name = 'Pointer'
    class_name = 'Glow'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    content = models.JSONField()
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    acl = models.ManyToManyField('ACL')


class Installation(SerializableMixin, models.Model):
    updateable_fields = (
        'user',
        'deviceType',
        'appVersion',
        'appName',
        'timeZone',
        'installationId',
        'appIdentifier',
        'localeIdentifier',
        'deviceName',
        'pushType',
        'deviceToken',
    )

    objectId = ObjectIDAutoField()
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    deviceType = models.CharField(max_length=128)
    appVersion = models.CharField(max_length=128)
    appName = models.CharField(max_length=128)
    timeZone = models.CharField(max_length=128)
    installationId = models.UUIDField(null=True)
    appIdentifier = models.CharField(max_length=128)
    localeIdentifier = models.CharField(max_length=128)
    deviceName = models.CharField(max_length=128)
    pushType = models.CharField(max_length=128)
    deviceToken = models.CharField(max_length=512)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    acl = models.ManyToManyField('ACL')
