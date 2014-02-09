from __future__ import unicode_literals

import json
import redis
import threading
import logging

from compatibility import urlopen

from config import POLLING_WAIT, REDIS_DB, REDIS_CHARSET, REDIS_PREFIX, REDIS_PORT, REDIS_HOST

from api.vkapi import method
from parallel import realtime, updates
from events.toggle import raise_event

UPDATE_RESULT = 'lp_result'

# from eventlet.green import urllib2


logger = logging.getLogger("cyvk")

__author__ = 'ernado'

LONG_POLLING_KEY = ':'.join([REDIS_PREFIX, 'long_polling_queue'])

def start_polling(jid):
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT,REDIS_DB, charset=REDIS_CHARSET)
    args = method('messages.getLongPollServer', jid)
    args['wait'] = POLLING_WAIT
    url = 'http://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode=2'.format(**args)
    r.lpush(LONG_POLLING_KEY, json.dumps({'jid': jid, 'url':url}))

def handle_url(jid, url):
    realtime.set_polling(jid)
    logger.debug('got url, starting polling')
    data = urlopen(url).read()
    logger.debug('got data from polling server')
    realtime.unset_polling(jid)
    raise_event(UPDATE_RESULT, response=data, jid=jid)

def event_handler(event_body):
    data = json.loads(event_body['response'])
    jid = event_body['jid']
    is_client = realtime.is_client(jid)

    try:
        if not data['updates']:
            logger.debug('no updates for %s' % jid)

        for update in data['updates']:
            updates.process_data(jid, update)
    except KeyError:
        logger.error('unable to process %s' % event_body)

    if is_client:
        start_polling(jid)
    else:
        logger.debug('ending polling for %s' % jid)


def loop():
    logger.debug('starting long polling loop')
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT,REDIS_DB, charset=REDIS_CHARSET)
    while True:
        request_raw = r.brpop(LONG_POLLING_KEY)[1]
        # { jid: 'user_jid', url: 'long_polling_url' }
        request = json.loads(request_raw)
        jid, url = request['jid'], request['url']
        t = threading.Thread(target=handle_url, args=(jid, url))
        t.start()


