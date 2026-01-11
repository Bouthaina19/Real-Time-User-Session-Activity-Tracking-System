import redis
from django.conf import settings

_redis_instance = None


def get_redis():
    global _redis_instance
    if _redis_instance is None:
        _redis_instance = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_instance  
