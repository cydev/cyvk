__author__ = 'ernado'

import logging

logger = logging.getLogger("vk4xmpp")

from config import REDIS_PORT, REDIS_HOST, REDIS_DB, REDIS_PREFIX, HOST, DEBUG_XMPPPY
import redis
import library.xmpp as xmpp


r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB)

CHANNEL_NAME = ':'.join([REDIS_PREFIX, 'stanzas_channel'])

class ComponentWrapper(object):
    def __init__(self):
        self.component = xmpp.Component(HOST, debug=DEBUG_XMPPPY)


    def register_handler(self, name, handler):
        self.component.RegisterHandler(name, handler(self).handle)


    def send(self, stanza):
        try:
            self.component.send(stanza)
        except KeyboardInterrupt:
            logger.debug('ignoring KeyboardInterrupt')
        except IOError as e:
            logger.error("couldn't send stanza: %s, %s" % (str(stanza), e))

def stanza_processing_thread(component):
    c = ComponentWrapper(component)


def send(stanza):
    p = r.pubsub()
    p.subscribe(CHANNEL_NAME)
    pass