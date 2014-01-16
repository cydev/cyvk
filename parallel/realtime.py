import redis
import time
import logging
import json
import database

from transport.stanza_queue import push
from transport.statuses import get_probe_stanza


from transport.config import REDIS_PREFIX, REDIS_HOST, REDIS_PORT, USE_LAST_MESSAGE_ID, API_MAXIMUM_RATE, POLLING_WAIT


logger = logging.getLogger("vk4xmpp")


r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, )


def probe_users():
    logger.info('probing users')

    users = database.get_all_users()

    for user in users:
        jid = user[0]
        logger.debug('probing %s' % jid)
        push(get_probe_stanza(jid))

def _get_last_message_key(jid):
    return _get_user_attribute_key(jid, 'last_message')

def set_last_message(jid, message_id):
    if not USE_LAST_MESSAGE_ID:
        return None

    logger.debug('DB: setting last message %s for %s' % (message_id, jid))

    r.set(_get_last_message_key(jid), message_id)
    #
    # with Database(DB_FILE) as db:
    #     db("UPDATE users SET lastMsgID=? WHERE jid=?", (message_id, jid))


_clients_key = ':'.join([REDIS_PREFIX, 'clients'])

def is_client(jid):
    return r.sismember(_clients_key, jid)

def is_user(jid):
    return r.sismember(_users_key, jid)


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
    # return r.get(_get_friends_key(uid)) or {}

    json_friends = json.loads(r.get(_get_friends_key(uid)))

    friends = {}

    for friend in json_friends:
        friends.update({int(friend): json_friends[friend]})
    # logger.debug('getting friends: %s' % friends)
    return friends

STATUS_ONLINE = 'online'
STATUS_OFFLINE = 'offline'
ONLINE_TIMEOUT = 60

# def set_online(uid):
#     key = _get_status_key(uid)
#     r.set(key, STATUS_ONLINE)
#     r.expire(key, ONLINE_TIMEOUT)
#
#
# def set_offline(uid):
#     logger.log('setting offline %s' % uid)
#     raise RuntimeError('fuck off, thats why')
#     # key = _get_status_key(uid)
#     # r.set(key, STATUS_OFFLINE)
#
# # def set_status(uid):
# #     key =
#
# def is_user_online(uid):
#     return r.get(_get_status_key(uid)) == STATUS_ONLINE


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


LAST_UPDATE = 'last_update'

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
    raw_data = r.smembers(_clients_key)

    # returning users as list of unicode strings
    return map(unicode, raw_data)

def reset_online_users():
    r.delete(_clients_key)

def add_online_user(jid):
    r.sadd(_clients_key, jid)

def remove_online_user(jid):
    r.srem(_clients_key, jid)


# self.jid, self.username, self.token, self.last_msg_id, self.roster_set = desc

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

    if not USE_LAST_MESSAGE_ID:
        return None

    try:
        return int(r.get(_get_last_message_key(jid)))
    except (TypeError, ValueError):
        # logger.error('get_last_message for %s error: %s' % (jid, e))
        return None


# def roster_subscribe(roster_set, jid):
#     # logger.debug('DB: subscribing %s for %s' % (roster_set, jid))
#     with Database(DB_FILE) as db:
#         db("UPDATE users SET rosterSet=? WHERE jid=?", (roster_set, jid))


USER_PREFIX = 'user'
TOKEN_PREFIX = 'token'
ACTIVITY = 'activity'

_users_key = ':'.join([REDIS_PREFIX, 'users'])


def _get_user_attribute_key(user, attribute):
    return ':'.join([REDIS_PREFIX, USER_PREFIX, user, attribute])

def _get_token_key(user):
    return _get_user_attribute_key(user, TOKEN_PREFIX)


def get_token(user):
    return r.get(_get_token_key(user))

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


# statuses:


# message queue

def _get_stanza_queue_key():
    return ':'.join([REDIS_PREFIX, 'queue'])






# processing lock

def _get_processing_key(jid):
    return _get_user_attribute_key(jid, 'is_processing')



def unset_processing(jid):
    r.set(_get_processing_key(jid), False)
    logger.debug('client %s processed' % jid)

def is_processing(jid):
    result =  r.get(_get_processing_key(jid))
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
    result =  r.get(_get_polling_key(jid))
    if result == 'False':
        return False
    return result








def set_processing(jid):
    logger.debug('processing client %s' % jid)
    k = _get_processing_key(jid)
    r.set(k, True)
    r.expire(k, 10)