from __future__ import unicode_literals

import redis
import logging
import threading
import json

from compatibility import text_type, binary_type
from config import REDIS_PREFIX, REDIS_PORT, REDIS_HOST, REDIS_DB, REDIS_CHARSET

logger = logging.getLogger("cyvk")

EVENTS_KEY = ':'.join([REDIS_PREFIX, 'events'])
NAME_KEY = 'name'


# user removed from transport
USER_REMOVED = 'user_removed'

# user registered via form
USER_REGISTERED = 'user_registered'

# user added
USER_ONLINE = 'user_online'

# long-polling result is delivered
UPDATE_RESULT = 'lp_result'

# long-polling start request
LP_REQUEST = 'lp_request'


all_events = (USER_REGISTERED, USER_REMOVED, USER_ONLINE)

class EventParsingException(Exception):
    pass


def raise_event(event_name, **params):
    event_body = {'name': event_name}
    event_body.update(params)
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)
    r.rpush(EVENTS_KEY, json.dumps(event_body))


class EventHandler(object):
    def __init__(self):
        self.handlers = {}

    def add_callback(self, event, callback):
        logger.debug('adding callback for %s' % event)

        if not isinstance(event, text_type):
            raise ValueError('event name must be %s' % text_type)

        if event not in all_events:
            raise ValueError('event %s not found' % event)

        if event not in self.handlers:
            self.handlers.update({event: set()})

        self.handlers[event].add(callback)

    def handle_event(self, event, event_body):
        if not isinstance(event, text_type):
            raise ValueError('event name must be %s' % text_type)

        if event not in all_events:
            raise ValueError('event %s not found' % event)

        if event not in self.handlers:
            logging.debug('no event handlers for %s' % event)
            return


    def _start(self):
        logger.debug('starting cyvk event handler')

        r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)

        while True:
            event = r.brpop(EVENTS_KEY)[1]
            logger.debug('got event %s' % event)

            if not isinstance(event, binary_type):
                raise TypeError('expected %s from redis, got %s' % (binary_type, type(event)))

            event_json = json.loads(event)

            if not isinstance(event_json, dict):
                raise EventParsingException('%s is not dict' % event_json)

            if NAME_KEY not in event_json:
                raise EventParsingException('event with no name: %s' % event_json)

            self.handle_event(event_json['name'].decode(REDIS_CHARSET), event_json)

    def start(self, block=False):
        if block:
            return self._start()

        t = threading.Thread(target=self._start, name='cyvk event loop')
        t.daemon = True
        t.start()