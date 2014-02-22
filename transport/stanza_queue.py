import pickle
import redis
from xmpp import Protocol as Stanza
from config import REDIS_HOST, REDIS_PORT, REDIS_PREFIX
import compat
logger = compat.get_logger()
r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, )


def _get_stanza_queue_key():
    return ':'.join([REDIS_PREFIX, 'queue'])


def enqueue():
    pickled_stanza = r.brpop(_get_stanza_queue_key())[1]
    stanza = pickle.loads(pickled_stanza)

    if not isinstance(stanza, Stanza):
        raise ValueError('expected stanza, deserialized %s' % type(stanza))

    return stanza