from __future__ import unicode_literals
import threading
import ujson as json

import redis

from compat import urlopen, get_logger
from config import POLLING_WAIT, REDIS_DB, REDIS_CHARSET, REDIS_PREFIX, REDIS_PORT, REDIS_HOST
from api.vkapi import Api
from parallel import realtime, updates
from events.toggle import raise_event


_logger = get_logger()
UPDATE_RESULT = 'lp_result'
LONG_POLLING_KEY = ':'.join([REDIS_PREFIX, 'long_polling_queue'])
START_POLLING_KEY = ':'.join([REDIS_PREFIX, 'long_polling_start_queue'])


def start_polling(jid):
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)
    r.lpush(START_POLLING_KEY, jid)


def _start_polling(jid, attempts=0):
    if realtime.is_polling(jid):
        return _logger.debug('%s is already polling' % jid)

    if attempts > 5:
        return _logger.error('too many long polling attempts for %s' % jid)

    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)
    api = Api(jid)
    args = api.messages.get_lp_server()
    args['wait'] = POLLING_WAIT
    url = 'http://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode=2'.format(**args)
    r.lpush(LONG_POLLING_KEY, json.dumps({'jid': jid, 'url': url}))


def _handle_url(jid, url):
    realtime.set_polling(jid)
    _logger.debug('got url, starting polling')
    data = urlopen(url).read()
    _logger.debug('got data from polling server')
    realtime.unset_polling(jid)
    raise_event(UPDATE_RESULT, response=data, jid=jid)


def event_handler(event_body):
    data = None
    try:
        data = json.loads(event_body['response'])
    except ValueError as e:
        _logger.error('unable to parse json: %s (%s)' % (data, e))
    jid = event_body['jid']
    is_client = realtime.is_client(jid)

    try:
        if not data['updates']:
            _logger.debug('no updates for %s' % jid)

        for update in data['updates']:
            updates.process_data(jid, update)
    except KeyError:
        _logger.error('unable to process %s' % event_body)

    if is_client:
        start_polling(jid)
    else:
        _logger.debug('ending polling for %s' % jid)


def loop_for_starting():
    _logger.debug('starting long polling starter loop')
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)

    while True:
        jid = r.brpop(START_POLLING_KEY)[1]
        jid = unicode(jid)
        t = threading.Thread(target=_start_polling, args=(jid, ))
        t.daemon = True
        t.start()


def loop():
    _logger.debug('starting long polling loop')
    r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)
    while True:
        request_raw = r.brpop(LONG_POLLING_KEY)[1]
        # { jid: 'user_jid', url: 'long_polling_url' }
        request = json.loads(request_raw)
        jid, url = request['jid'], request['url']
        t = threading.Thread(target=_handle_url, args=(jid, url))
        t.daemon = True
        t.start()


def start_thread_lp():
    lp_thread = threading.Thread(target=loop, name='long polling thread')
    lp_thread.daemon = True
    lp_thread.start()

    return lp_thread


def start_thread_lp_requests():
    lp_rq_thread = threading.Thread(target=loop_for_starting, name='long polling requests thread')
    lp_rq_thread.daemon = True
    lp_rq_thread.start()

    return lp_rq_thread