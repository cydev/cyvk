import time
import logging
import ujson as json

import redis

from config import REDIS_PREFIX, REDIS_HOST, REDIS_PORT, API_MAXIMUM_RATE, POLLING_WAIT


logger = logging.getLogger("cyvk")

r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, )

LAST_UPDATE = 'last_update'
STATUS_ONLINE = 'online'
STATUS_OFFLINE = 'offline'
ONLINE_TIMEOUT = 60
USER_PREFIX = 'user'
TOKEN_PREFIX = 'token'
ACTIVITY = 'activity'
USERS_KEY = ':'.join([REDIS_PREFIX, 'users'])
CLIENTS_KEY = ':'.join([REDIS_PREFIX, 'clients'])


def _get_user_attribute_key(user, attribute):
    return ':'.join([REDIS_PREFIX, USER_PREFIX, user, attribute])


def _get_last_message_key(jid):
    return _get_user_attribute_key(jid, 'last_message')


def set_last_message(jid, message_id):
    logger.debug('DB: setting last message %s for %s' % (message_id, jid))

    r.set(_get_last_message_key(jid), message_id)


def is_client(jid):
    return r.sismember(CLIENTS_KEY, jid)


def is_user(jid):
    return r.sismember(USERS_KEY, jid)


def _get_last_method_time_key(jid):
    return _get_user_attribute_key(jid, 'last_method_time')


def get_last_method_time(jid):
    # last vk api request time
    # for burst protection
    try:
        return float(r.get(_get_last_method_time_key(jid)))
    except (TypeError, ValueError):
        return 0


def update_last_method_time(jid):
    now = time.time()
    r.set(_get_last_method_time_key(jid), now)


def wait_for_api_call(jid):
    """
    Waits until there is API_MAXIMUM_RATE seconds between api calls
    @type jid: unicode
    @param jid: client jid
    """

    assert isinstance(jid, unicode)

    now = time.time()
    last_time = get_last_method_time(jid)
    diff = now - last_time

    if diff < API_MAXIMUM_RATE:
        # logger.debug('Burst protection succeeded')
        time.sleep(abs(diff - API_MAXIMUM_RATE))

    update_last_method_time(jid)


def _get_friends_key(uid):
    return _get_user_attribute_key(uid, 'friends')


def _get_status_key(uid):
    return _get_user_attribute_key(uid, 'status')


def get_friends(uid):
    # logger.debug('get_friends for %s' % uid)
    friends_raw = json.loads(r.get(_get_friends_key(uid)))
    friends = {}

    for friend in friends_raw:
        friends.update({int(friend): friends_raw[friend]})
    # logger.debug('getting friends: %s' % friends)
    return friends


def set_friends(uid, friends):
    friends_json = json.dumps(friends)
    # logger.debug('setting friends %s' % friends_json)
    r.set(_get_friends_key(uid), friends_json)


def _get_last_activity_key(uid):
    return _get_user_attribute_key(uid, ACTIVITY)


def get_last_activity(user):
    try:
        return float(r.get(_get_last_activity_key(user)))
    except (TypeError, ValueError):
        return 0


def _get_last_update_key(uid):
    return _get_user_attribute_key(uid, LAST_UPDATE)


def get_last_update(uid):
    last_update = r.get(_get_last_update_key(uid))
    try:
        return float(last_update)
    except TypeError:
        return 0


def set_last_update_now(uid):
    last_update = time.time()
    r.set(_get_last_update_key(uid), last_update)


def get_clients():
    # getting user list as raw strings
    raw_data = r.smembers(CLIENTS_KEY)

    # returning users as list of unicode strings
    return map(unicode, raw_data)


def reset_online_users():
    r.delete(CLIENTS_KEY)


def add_online_user(jid):
    r.sadd(CLIENTS_KEY, jid)


def remove_online_user(jid):
    r.srem(CLIENTS_KEY, jid)


def _get_roster_set_flag_key(jid):
    return _get_user_attribute_key(jid, 'is_roster_set')


def is_roster_set(jid):
    result = r.get(_get_roster_set_flag_key(jid))
    if result:
        return True
    else:
        return False


def set_roster_flag(jid):
    r.set(_get_roster_set_flag_key(jid), True)


def _get_username_key(jid):
    return _get_user_attribute_key(jid, 'username')


def get_username(jid):
    return r.get(_get_friends_key(jid))


def set_username(jid, username):
    return r.set(_get_username_key(jid), username)


def get_last_message(jid):
    try:
        return int(r.get(_get_last_message_key(jid)))
    except (TypeError, ValueError):
        # logger.error('get_last_message for %s error: %s' % (jid, e))
        return None


def _get_token_key(user):
    return _get_user_attribute_key(user, TOKEN_PREFIX)


def get_token(user):
    t = r.get(_get_token_key(user))
    # logger.debug('got token %s' % t)
    return t


def set_last_activity(user, activity_time):
    # logger.debug('setting last activity %s for %s' % (activity_time, user))
    r.set(_get_last_activity_key(user), activity_time)


def set_last_activity_now(user):
    now = time.time()
    set_last_activity(user, now)


def _get_last_status_key(jid):
    return _get_user_attribute_key(jid, 'last_status')


def get_last_status(jid):
    return r.get(_get_last_status_key(jid))


def set_last_status(jid, status):
    return r.set(_get_last_status_key(jid), status)


def _get_processing_key(jid):
    return _get_user_attribute_key(jid, 'is_processing')


def unset_processing(jid):
    r.set(_get_processing_key(jid), False)
    logger.debug('client %s processed' % jid)


def is_processing(jid):
    result = r.get(_get_processing_key(jid))
    if result == 'False':
        return False
    return result


def _get_polling_key(jid):
    return _get_user_attribute_key(jid, 'is_polling')


def set_polling(jid):
    logger.debug('polling client %s' % jid)
    k = _get_polling_key(jid)
    r.set(k, True)
    r.expire(k, POLLING_WAIT)


def unset_polling(jid):
    r.set(_get_polling_key(jid), False)
    logger.debug('client %s processed' % jid)


def is_polling(jid):
    result = r.get(_get_polling_key(jid))
    if result == 'False':
        return False
    return result


def set_token(jid, token):
    logger.debug('setting token %s' % token)
    r.set(_get_token_key(jid), token)


def set_processing(jid):
    logger.debug('processing client %s' % jid)
    k = _get_processing_key(jid)
    r.set(k, True)
    r.expire(k, 10)


def initialize_user(jid, token, last_msg_id, roster_set):
    r.sadd(USERS_KEY, jid)
    if roster_set:
        set_roster_flag(jid)
    set_last_message(jid, last_msg_id)
    set_token(jid, token)
    set_friends(jid, {})
