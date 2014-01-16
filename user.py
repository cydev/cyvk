from __future__ import unicode_literals

import time
import logging
import threading
import json
import urllib2

from config import TRANSPORT_ID, USE_LAST_MESSAGE_ID, IDENTIFIER, POLLING_WAIT
from database import set_token
from friends import get_friend_jid
import webtools as webtools

import messaging
import realtime

import xmpp as xmpp
from errors import CaptchaNeeded, TokenError, AuthenticationException
from async_api import tail_call_optimized
import updates
from vkapi import method, is_application_user, mark_messages_as_read, get_messages

import database


logger = logging.getLogger("vk4xmpp")


def set_online(user):
    m = "account.setOnline"
    method(m, user)


def update_last_activity(uid):
    logger.debug('updating last activity')
    realtime.set_last_activity(uid, time.time())


def get_friends(jid, fields=None):
    logger.debug('getting friends from api for %s' % jid)
    fields = fields or ["screen_name"]
    friends_raw = method("friends.get", jid, {"fields": ",".join(fields)}) or {} # friends.getOnline
    friends = {}
    for friend in friends_raw:
        uid = friend["uid"]
        name = messaging.escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
        try:
            friends[uid] = {"name": name, "online": friend["online"]}
            for key in fields:
                if key != "screen_name":
                    friends[uid][key] = friend.get(key)
        except KeyError as key_error:
            logger.debug('%s while processing %s' % (key_error, uid))
            continue
    return friends


def send_presence(target, jid_from, presence_type=None, nick=None, reason=None):
    logger.debug('sending presence for %s about %s' % (target, jid_from))
    presence = xmpp.Presence(target, presence_type, frm=jid_from, status=reason)
    if nick:
        presence.setTag("nick", namespace=xmpp.NS_NICK)
        presence.setTagData("nick", nick)
    realtime.queue_stanza(presence)
    # gateway.send(presence)


def roster_subscribe(jid, subscriptions=None):
    """
    Subscribe user for jids in dist
    """
    logger.debug('roster_subscribe for %s: %s' % (jid, subscriptions.keys()))

    if not subscriptions:
        send_presence(jid, TRANSPORT_ID, "subscribe", IDENTIFIER["name"])
        return

    for uid, value in subscriptions.iteritems():
        send_presence(jid, get_friend_jid(uid), "subscribe", value["name"])


def send_messages(jid):
    logger.debug('user api: send_messages for %s' % jid)

    if not jid:
        raise ValueError('user api: unable to send messages for blank jid')

    last_message = realtime.get_last_message(jid)

    messages = get_messages(jid, 200, last_message)

    if not messages:
        return

    messages = sorted(messages[1:], messaging.sorting)

    if not messages:
        return

    read = []

    last_message = messages[-1]["mid"]

    if USE_LAST_MESSAGE_ID:
        database.set_last_message(jid, last_message)

    for message in messages:
        read.append(str(message["mid"]))
        from_jid = get_friend_jid(message["uid"])
        body = webtools.unescape(message["body"])
        body += messaging.parse(jid, message)
        messaging.send(jid, messaging.escape("", body), from_jid, message["date"])

    mark_messages_as_read(jid, read)
    # self.vk.msg_mark_as_read(read)
    # if USE_LAST_MESSAGE_ID:
    #     database.set_last_message(last_msg_id, self.jid)


def get_user_data(uid, target_uid, fields=None):
    logger.debug('user api: sending user data for %s about %s' % (uid, target_uid))
    fields = fields or ["screen_name"]
    args = {"fields": ",".join(fields), "user_ids": target_uid}
    m = "users.get"
    data = method(m, uid, args)

    if data:
        data = data[0]
        data["name"] = messaging.escape_name("", u"%s %s" % (data["first_name"], data["last_name"]))
        del data["first_name"], data["last_name"]
    else:
        data = {}
        for key in fields:
            data[key] = "Unknown error when trying to get user data. We're so sorry."
    return data


def send_message(jid, body, destination_uid):
    logger.debug('user api: message to %s' % destination_uid)

    assert isinstance(jid, unicode)
    assert isinstance(destination_uid, unicode)
    assert isinstance(body, unicode)

    method_name = "messages.send"
    method_values = {'user_id': int(destination_uid), "message": body, "type": 0}
    update_last_activity(jid)

    return method(method_name, jid, method_values)


def send_init_presence(jid):
    """
    Sends initial presences to user about friends and transport
    @type jid: unicode
    @param jid: user jid
    @return: None
    """
    assert isinstance(jid, unicode)
    friends = realtime.get_friends(jid)
    assert isinstance(friends, dict)
    online_friends = filter(lambda uid: friends[uid]['online'], friends)
    logger.debug('user api: sending initial status to %s, with friends: %s' % (jid, online_friends != {}))

    for friend_uid in online_friends:
        send_presence(jid, get_friend_jid(friend_uid), nick=friends[friend_uid]['name'])

    # sending transport presence
    send_presence(jid, TRANSPORT_ID, nick=IDENTIFIER["name"])


def send_out_presence(jid, reason=None):
    assert isinstance(jid, unicode)

    status = "unavailable"
    logger.debug("user api: sending out presence for %s" % jid)
    notification_list = realtime.get_friends(jid).keys() + [TRANSPORT_ID]

    for uid in notification_list:
        send_presence(jid, get_friend_jid(uid), status, reason=reason)


def delete_user(jid, roster=False):
    logger.debug("user api: delete_user %s" % jid)

    assert isinstance(jid, unicode)

    database.remove_user(jid)
    friends = realtime.get_friends(jid)

    if roster and friends:
        logger.debug("user api: removing %s roster" % jid)
        for friend_id in friends:
            friend_jid = get_friend_jid(friend_id)
            send_presence(jid, friend_jid, "unsubscribe")
            send_presence(jid, friend_jid, "unsubscribed")
        realtime.set_offline(jid)

    database.remove_user(jid)
    database.remove_online_user(jid)


def update_friends(jid):
    friends_vk = get_friends(jid)
    friends_db = realtime.get_friends(jid)

    assert isinstance(jid, unicode)
    assert isinstance(friends_vk, dict)
    assert isinstance(friends_db, dict)

    # logger.debug('in db: %s, from vk: %s' % (len(friends_db), len(friends_vk)))
    #
    # logger.debug('in db: %s' % friends_db)
    # logger.debug('from vk: %s' % friends_vk)

    if friends_db == friends_vk:
        logger.debug('no changes in friend list for %s' % jid)
        return

    logger.debug('updating friend list for %s' % jid)

    subscriptions = {}
    update_status_dict = {}

    for uid in friends_vk:
        friend = friends_vk[uid]

        if uid not in friends_db:
            logger.debug('friend %s not found' % uid)
            subscriptions.update({uid: friend})
            continue

        if friends_db[uid]['online'] != friend['online']:
            logger.debug('friend %s status changed' % uid)
            status = None if friend["online"] else "unavailable"
            update_status_dict.update({uid: status})

    roster_subscribe(jid, subscriptions)

    for uid, status in update_status_dict.items():
        send_presence(jid, get_friend_jid(uid), status)

    database.set_friends(jid, friends_vk)


# def is_timed_out(jid):
#     assert isinstance(jid, unicode)
#
#     now = time.time()
#     last_activity = database.get_last_activity(jid)
#
#     # logger.debug('last activity for %s is %s' % (jid, last_activity))
#     # logger.debug('now is %s' % now)
#
#     # last_update = database.get_last_update(jid)
#
#     user_inactive = (now - last_activity) > ACTIVE_TIMEOUT
#     # roster_timeout = (now - last_update) > ROSTER_TIMEOUT
#
#     return user_inactive


def initialize(jid, send=True):
    """
    Initializes user by subscribing to friends and sending initial presence
    @type jid: unicode
    @param jid: client jid
    @param send: send presence flag
    """
    logger.debug("user api: called init for user %s" % jid)

    assert isinstance(jid, unicode)

    # getting friends from vk api
    friends = get_friends(jid)

    # updating user in redis
    database.set_friends(jid, friends)
    realtime.unset_polling(jid)
    realtime.unset_processing(jid)
    realtime.set_online(jid)

    if friends:
        logger.debug("user api: subscribing friends for %s" % jid)
        roster_subscribe(jid, friends)

    if send:
        logger.debug('sending initial presence')
        send_init_presence(jid)


def load(jid):
    # self.vk = VKLogin(gateway, token, jid)

    logger.debug("user api: loading %s" % jid)
    desc = database.get_description(jid)

    if not desc:
        raise ValueError('user api: user not found %s' % jid)

    # if not self.token or not self.password:
    logger.debug("user api: %s exists in db" % jid)
    jid = desc['jid']

    # database.set_username(jid, desc['username'])
    database.set_last_message(jid, desc['last_message_id'])
    if desc['roster_set_flag']:
        database.set_roster_flag(jid)

    database.set_friends(jid, {})

    logger.debug("user api: %s data loaded" % jid)


def connect(jid, token):
    logger.debug("user api: connecting %s" % jid)
    # vk = VKLogin(gateway, token, jid)

    if not token:
        raise AuthenticationException('no token for %s' % jid)

    # logger.debug("user api: vk api initialized")
    try:
        logger.debug('user api: trying to auth with token')
        set_token(jid, token)
        is_application_user(jid)
        logger.debug("user api: authenticated %s" % jid)
    except CaptchaNeeded:
        logger.debug("user api: captcha needed for %s" % jid)
        roster_subscribe(jid)
        raise NotImplementedError('Captcha')
        # self.vk.captcha_challenge()
        # return True
    except TokenError as token_error:
        if token_error.message == "User authorization failed: user revoke access for this token.":
            logger.critical("user api: %s" % token_error.message)
            delete_user(jid)
        elif token_error.message == "User authorization failed: invalid access_token.":
            send_message(jid, token_error.message + " Please, register again", TRANSPORT_ID)
        raise AuthenticationException('invalid token')
        # except Exception as e:
    #     # TODO: We can crash there
    #     logger.debug('Auth failed: %s' % e)
    #     raise
    #     # dump_crash("TUser.Connect")
    #     # return False

    logger.debug("user api: updating db for %s" % jid)
    if not realtime.is_user(jid):
        raise NotImplementedError('insertion to database')
        # database.insert_user(jid, self.username, token, self.last_msg_id, self.roster_set)
    # elif self.password:
    #     database.set_token(self.jid, token)
    # try:
    #     m = "users.get"
    #     # t = self.vk.method("users.get")
    #     t = method(m, jid)
    #     user_id = t[0]["uid"]
    # except (KeyError, TypeError):
    #     raise AuthenticationException('could not recieve user id')

    # self.gateway.jid_to_id[self.user_id] = self.jid
    # self.friends = self.vk.get_friends()
    realtime.set_online(jid)
    realtime.set_last_activity_now(jid)

@tail_call_optimized
def _long_polling_get(jid):
    if realtime.is_polling(jid):
        logger.debug('already polling %s' % jid)
        return

    realtime.set_polling(jid)
    logger.debug('getting data via long polling')
    long_polling = method('messages.getLongPollServer', jid)
    long_polling['wait'] = POLLING_WAIT
    url = 'http://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode=2'.format(**long_polling)
    logger.debug('got url, starting polling')
    realtime.wait_for_api_call(jid)
    data = json.loads(urllib2.urlopen(url).read())
    logger.debug('got data from polling server')
    realtime.unset_polling(jid)

    if not data['updates']:
        logger.debug('no updates for %s' % jid)
        return _long_polling_get(jid)

    for update in data['updates']:
        updates.process_data(jid, update)

    # logger.debug('response: %s' % data)

    if realtime.is_client(jid):
        _long_polling_get(jid)
    else:
        logger.debug('finishing polling for %s' % jid)
    # process_client(jid)

def process_client(jid):
    """
    Updates client messages, friends and status
    @type jid: unicode
    @param jid: client jid
    @return:
    """
    assert isinstance(jid, unicode)

    if realtime.is_processing(jid):
        logger.debug('already processing client %s' % jid)
        return

    # blocking processing
    realtime.set_processing(jid)

    # checking user status
    if not realtime.is_user_online(jid):
        logger.debug('user %s offline' % jid)
        database.remove_online_user(jid)
        return

    # checking user time out
    # if is_timed_out(jid):
    #     logger.debug('timeout for client %s' % jid)
    #     database.remove_online_user(jid)
    #     return


    t = threading.Thread(target=_long_polling_get, args=(jid, ), name='long polling for %s' % jid)

    if not realtime.is_polling(jid):
        update_friends(jid)
        send_messages(jid)
        t.start()
    else:
        logger.debug('updates for %s are handled by polling' % jid)

    realtime.unset_processing(jid)


def update_transports_list(jid, add=True):
    is_client = realtime.is_client(jid)
    if not is_client:
        if add:
            realtime.add_online_user(jid)
        else:
            database.remove_online_user(jid)

    process_client(jid)

def remove_user(jid):
    logger.debug('remove_user %s' % jid)
    is_client = realtime.is_client(jid)
    if not is_client:
        logger.debug('%s already not in transport')
        return
    database.remove_online_user(jid)
    process_client(jid)

def process_users():
    now = time.time()
    clients = realtime.get_clients()

    if not clients:
        logger.debug('no clients')
        return

    l = len(map(process_client, clients))

    logger.debug('iterated for %.2f ms - %s users' % ((time.time() - now)*1000, l))

def make_client(jid):
    assert isinstance(jid, unicode)

    logger.debug('add_user %s' % jid)
    if realtime.is_client(jid):
       logger.debug('%s already a client' % jid)
       return
    realtime.add_online_user(jid)
    process_client(jid)

    # def connect(gateway, jid):
    #         # jid = self.jid
    #         authenticated = False
    #         token = database.get_token(jid)
    #         # token = self.token
    #         # gateway = self.gateway
    #
    #         logger.debug("TUser: connecting %s" % jid)
    #         is_online = False
    #         # noinspection PyBroadException
    #         try:
    #             logger.debug('TUser: trying to auth with token %s' % token)
    #             database.set_token(jid, token)
    #             authenticated = self.vk.auth(token)
    #             logger.debug("TUser: auth=%s for %s" % (authenticated, jid))
    #         except CaptchaNeeded:
    #             logger.debug("TUser: captcha needed for %s" % jid)
    #             roster_subscribe(gateway, jid)
    #             self.vk.captcha_challenge()
    #             return True
    #         except TokenError as token_error:
    #             if token_error.message == "User authorization failed: user revoke access for this token.":
    #                 logger.critical("TUser: %s" % token_error.message)
    #                 delete_user(jid)
    #             elif token_error.message == "User authorization failed: invalid access_token.":
    #                 msg_send(gateway.component, self.jid,
    #                          stext._(token_error.message + " Please, register again"), TRANSPORT_ID)
    #             is_online = False
    #         except Exception as e:
    #             # TODO: We can crash there
    #             logger.debug('Auth failed: %s' % e)
    #             raise
    #             # dump_crash("TUser.Connect")
    #             # return False
    #
    #         token = self.vk.get_token()
    #         if authenticated and token:
    #             logger.debug("TUser: updating db for %s because auth done " % self.jid)
    #             t = None
    #             if not self.exists_id_db:
    #                 database.add_user(self.jid, self.username, token, self.last_msg_id, self.roster_set)
    #             elif self.password:
    #                 database.set_token(self.jid, token)
    #             try:
    #                 m = "users.get"
    #                 # t = self.vk.method("users.get")
    #                 t = method(m, self.jid)
    #                 self.user_id = t[0]["uid"]
    #             except (KeyError, TypeError):
    #                 logger.error("TUser: could not recieve user id. JSON: %s" % str(t))
    #                 self.user_id = 0
    #
    #             # self.gateway.jid_to_id[self.user_id] = self.jid
    #             # self.friends = self.vk.get_friends()
    #             database.set_online(self.jid)
    #             is_online = True
    #
    #         if not USE_LAST_MESSAGE_ID:
    #             self.last_msg_id = 0
    #         return is_online