import json
import redis
import threading
import logging
from compatibility import text_type, binary_type
from config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_CHARSET
from events.constants import all_events, EVENTS_KEY, NAME_KEY
from parallel.long_polling import event_handler, UPDATE_RESULT

__author__ = 'ernado'
logger = logging.getLogger("cyvk")


class EventParsingException(Exception):
    pass

class EventHandler(object):
    def __init__(self):
        self.handlers = {}
        self.events = all_events
        self.add_event(UPDATE_RESULT)
        self.add_callback(UPDATE_RESULT, event_handler)

    def add_event(self, event_name):
        self.events.add(event_name)

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
            logger.debug('no event handlers for %s' % event)
            return

        handlers = self.handlers[event]

        for handler in handlers:
            # TODO: async
            handler(event_body)


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