import redis
from config import REDIS_PORT, REDIS_HOST, REDIS_DB, REDIS_CHARSET
from events.constants import EVENTS_KEY
import ujson as json


def raise_event(event_name, **params):
    event_body = {'name': event_name}
    event_body.update(params)
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)
    r.rpush(EVENTS_KEY, json.dumps(event_body))