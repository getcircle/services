from django.conf import settings
import redis


def get_redis_client():
    return redis.StrictRedis(**settings.SERVICES_REDIS)
