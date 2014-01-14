import time
import logging

from config import TRANSPORT_ID, USE_LAST_MESSAGE_ID, IDENTIFIER, ACTIVE_TIMEOUT
from vklogin import VKLogin
from messaging import msg_send, msg_sort, escape_name, escape_message
import library.webtools as webtools
from vklogin import get_messages, mark_messages_as_read
from vk2xmpp import jid_from_uid
import library.xmpp as xmpp
from errors import CaptchaNeeded, TokenError
from errors import AuthenticationException
import vklogin as login_api

from library.vkapi import method

logger = logging.getLogger("vk4xmpp")

import library.stext as stext

import database

def set_online(user):
    m = "account.setOnline"
    method(m, user)


def update_last_activity(uid):
    logger.debug('updating last activity')
    database.set_last_activity(uid, time.time())

def get_friends(jid, fields=None):
    logger.debug('getting friends from api for %s' % jid)
    fields = fields or ["screen_name"]
    friends_raw = method("friends.get", jid, {"fields": ",".join(fields)}) or {} # friends.getOnline
    friends = {}
    for friend in friends_raw:
        uid = friend["uid"]
        name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
        try:
            friends[uid] = {"name": name, "online": friend["online"]}
            for key in fields:
                if key != "screen_name":
                    friends[uid][key] = friend.get(key)
        except KeyError as key_error:
            logger.debug('%s while processing %s' % (key_error, uid))
            continue
    return friends


class TUser(object):
    def __init__(self, gateway, token, jid):
        self.password = None
        self.gateway = gateway

        self.friends = {}
        self.auth = None
        self.token = token
        self.last_msg_id = None
        # self.roster_set = None
        self.exists_id_db = None
        self.last_status = None
        self.last_activity = time.time()
        self.last_update = time.time()
        self.jid = jid
        self.resources = []
        self.chat_users = {}
        self.user_id = None
        self.vk = VKLogin(gateway, token, jid)

        logger.debug("TUSER init %s" % self.jid)
        desc = database.get_description(self.jid)

        if not desc:
            raise ValueError('user not found %s' % self.jid)

        # if not self.token or not self.password:
        logger.debug("TUser: %s exists in db" % self.jid)
        self.exists_id_db = True
        self.jid = desc['jid']
        self.username = desc['username']
        self.last_msg_id = desc['last_message_id']
        self.roster_set = desc['roster_set_flag']

        database.set_friends(self.jid, {})

        logger.debug("TUser: %s data loaded" % self.jid)
        # self.jid, self.username, self.token, self.last_msg_id, self.roster_set = desc
        # elif self.password or self.token:
        #     logger.debug("TUser: %s exists in db. Will be deleted." % self.jid)
        #     run_thread(delete_user(self.jid))

    def __repr__(self):
        return '<TUser %s>' % self.jid


    # noinspection PyShadowingNames
    # def msg(self, body, recipient_uid, m_type="user_id"):
    #     logger.debug('TUser: msg to %s' % recipient_uid)
    #     method_name = "messages.send"
    #     method_values = {m_type: recipient_uid, "message": body, "type": 0}
    #     # noinspection PyBroadException
    #     try:
    #         update_last_activity(self.jid)
    #         a = database.get_last_activity(self.jid)
    #         return method(method_name, self.jid, method_values)
    #         # msg = self.vk.method("messages.send", {m_type: uid, "message": body, "type": 0})
    #     except Exception as e:
    #         logger.error('messages.send: %s' % e)
    #         dump_crash("messages.send")
    #         return False

    def connect(self):
        jid = self.jid
        authenticated = False
        token = self.token
        gateway = self.gateway

        logger.debug("TUser: connecting %s" % jid)
        is_online = False
        # noinspection PyBroadException
        try:
            logger.debug('TUser: trying to auth with token')
            database.set_token(jid, token)
            authenticated = self.vk.auth(jid, token)
            logger.debug("TUser: auth=%s for %s" % (authenticated, jid))
        except CaptchaNeeded:
            logger.debug("TUser: captcha needed for %s" % jid)
            roster_subscribe(gateway, jid)
            raise NotImplementedError('Captcha')
            # self.vk.captcha_challenge()
            # return True
        except TokenError as token_error:
            if token_error.message == "User authorization failed: user revoke access for this token.":
                logger.critical("TUser: %s" % token_error.message)
                delete_user(self.jid)
            elif token_error.message == "User authorization failed: invalid access_token.":
                msg_send(self.gateway.component, self.jid,
                         stext._(token_error.message + " Please, register again"), TRANSPORT_ID)
            is_online = False
        except Exception as e:
            # TODO: We can crash there
            logger.debug('Auth failed: %s' % e)
            raise
            # dump_crash("TUser.Connect")
            # return False

        token = self.vk.get_token()
        if authenticated and token:
            logger.debug("TUser: updating db for %s because auth done " % self.jid)
            t = None
            if not database.is_user(self.jid):
                database.insert_user(self.jid, self.username, token, self.last_msg_id, self.roster_set)
            elif self.password:
                database.set_token(self.jid, token)
            try:
                m = "users.get"
                # t = self.vk.method("users.get")
                t = method(m, self.jid)
                self.user_id = t[0]["uid"]
            except (KeyError, TypeError):
                logger.error("TUser: could not recieve user id. JSON: %s" % str(t))
                self.user_id = 0

            # self.gateway.jid_to_id[self.user_id] = self.jid
            # self.friends = self.vk.get_friends()
            database.set_online(self.jid)
            is_online = True

        if not USE_LAST_MESSAGE_ID:
            self.last_msg_id = 0
        return is_online

    def init(self, force=False, send=True):
        logger.debug("TUser: called init for user %s" % self.jid)
        friends = get_friends(self.jid)
        database.set_friends(self.jid, friends)

        if friends and not self.roster_set or force:
            logger.debug("TUser: calling subscribe with force:%s for %s" % (force, self.jid))
            self.roster_subscribe(self.friends)
        if send:
            send_init_presence(self.gateway, self.jid)

    def send_presence(self, target, jid_from, p_type=None, nick=None, reason=None):
        logger.debug('sending presence for %s about %s' % (target, jid_from))
        presence = xmpp.Presence(target, p_type, frm=jid_from, status=reason)
        if nick:
            presence.setTag("nick", namespace=xmpp.NS_NICK)
            presence.setTagData("nick", nick)
        self.gateway.send(presence)

    # def send_init_presence(self):
    #     logger.debug('sending init presence')
    #     self.friends = database.get_friends(self.jid)
    #     # too too bad way to do it again. But it's a guarantee of the availability of friends.
    #     logger.debug("TUser: sending init presence to %s (friends %s)" % \
    #                  (self.jid, "exists" if self.friends else "empty"))
    #     for uid, value in self.friends.iteritems():
    #         if value["online"]:
    #             self.send_presence(self.jid, jid_from_uid(uid), None, value["name"])
    #     self.send_presence(self.jid, TRANSPORT_ID, None, IDENTIFIER["name"])

    # def send_out_presence(self, target, reason=None):
    #     # TODO: Why this needed?
    #     p_type = "unavailable"
    #     logger.debug("TUser: sending out presence to %s" % self.jid)
    #     for uid in self.friends.keys() + [TRANSPORT_ID]:
    #         self.send_presence(target, jid_from_uid(uid), p_type, reason=reason)

    def roster_subscribe(self, dist=None):
        dist = dist or {}
        for uid, value in dist.iteritems():
            self.send_presence(self.jid, jid_from_uid(uid), "subscribe", value["name"])
        self.send_presence(self.jid, TRANSPORT_ID, "subscribe", IDENTIFIER["name"])

        if dist:
            # self.roster_set = True
            database.roster_subscribe(self.roster_set, self.jid)

    def get_user_data(self, uid, fields=None):
        logger.debug('TUser: sending user data for %s' % uid)
        fields = fields or ["screen_name"]
        data = self.vk.method("users.get", {"fields": ",".join(fields), "user_ids": uid})
        print 'User data:'
        print data
        if data:
            data = data[0]
            data["name"] = escape_name("", u"%s %s" % (data["first_name"], data["last_name"]))
            del data["first_name"], data["last_name"]
        else:
            data = {}
            for key in fields:
                data[key] = "Unknown error when trying to get user data. We're so sorry."
        return data

    def send_messages(self):
        logger.debug('TUser: send_messages for %s' % self.jid)

        messages = get_messages(self.jid, 200, self.last_msg_id if USE_LAST_MESSAGE_ID else None)

        if not messages:
            return

        messages = messages[1:]
        messages = sorted(messages, msg_sort)

        if not messages:
            return

        read = []
        self.last_msg_id = messages[-1]["mid"]

        usr = self

        for message in messages:
            read.append(str(message["mid"]))
            from_jid = jid_from_uid(message["uid"])
            body = webtools.unescape(message["body"])

            def process_handler(func):
                # try:
                return func(usr, message)
                # except Exception as e:
                #     logger.error('Error while processing handlers: %s' % e)
                #     dump_crash("handle.%s" % func.func_name)
                #     raise e

            body += ''.join(map(process_handler, self.gateway.handlers))

            # for func in self.gateway.handlers:
            #     try:
            #         result = func(self, message)
            #     except Exception as e:
            #         logger.error('Error while processing handlers: %s' % e)
            #         dump_crash("handle.%s" % func.func_name)
            #         raise e
            #     if result is None:
            #         for func in self.gateway.handlers:
            #             f_apply(func, (self, message))
            #         break
            #     else:
            #         body += result
            # else:
            msg_send(self.gateway.component, self.jid, escape_message("", body), from_jid, message["date"])

        mark_messages_as_read(self.jid, read)
        # self.vk.msg_mark_as_read(read)
        if USE_LAST_MESSAGE_ID:
            database.set_last_message(self.last_msg_id, self.jid)

    def try_again(self):
        logger.debug("calling reauth for user %s" % self.jid)
        # try:
        if not self.vk.is_online:
            self.connect()
        self.init(True)
        # except:
        #     dump_crash("tryAgain")

def send_presence(gateway, target, jid_from, presence_type=None, nick=None, reason=None):
    logger.debug('sending presence for %s about %s' % (target, jid_from))
    presence = xmpp.Presence(target, presence_type, frm=jid_from, status=reason)
    if nick:
        presence.setTag("nick", namespace=xmpp.NS_NICK)
        presence.setTagData("nick", nick)
    gateway.send(presence)

def roster_subscribe(gateway, jid, subscriptions=None):
    """
    Subscribe user for jids in dist
    """
    logger.debug('roster_subscribe for %s: %s' % (jid, subscriptions.keys()))

    if not subscriptions:
        send_presence(gateway, jid, TRANSPORT_ID, "subscribe", IDENTIFIER["name"])
        return

    for uid, value in subscriptions.iteritems():
        send_presence(gateway, jid_from_uid(uid), jid, "subscribe", value["name"])


def send_messages(gateway, jid):
    logger.debug('user api: send_messages for %s' % jid)

    last_message = database.get_last_message(jid)

    messages = get_messages(jid, 200, last_message)

    if not messages:
        return

    messages = messages[1:]
    messages = sorted(messages, msg_sort)

    if not messages:
        return

    read = []

    last_message = messages[-1]["mid"]

    if USE_LAST_MESSAGE_ID:
        database.set_last_message(jid, last_message)

    for message in messages:
        read.append(str(message["mid"]))
        from_jid = jid_from_uid(message["uid"])
        body = webtools.unescape(message["body"])

        def process_handler(func):
            # try:
            return func(None, message)
            # except Exception as e:
            #     logger.error('Error while processing handlers: %s' % e)
            #     dump_crash("handle.%s" % func.func_name)
            #     raise e

        body += u''.join(map(process_handler, gateway.handlers))

        # for func in self.gateway.handlers:
        #     try:
        #         result = func(self, message)
        #     except Exception as e:
        #         logger.error('Error while processing handlers: %s' % e)
        #         dump_crash("handle.%s" % func.func_name)
        #         raise e
        #     if result is None:
        #         for func in self.gateway.handlers:
        #             f_apply(func, (self, message))
        #         break
        #     else:
        #         body += result
        # else:
        msg_send(gateway.component, jid, escape_message("", body), from_jid, message["date"])

    mark_messages_as_read(jid, read)
    # self.vk.msg_mark_as_read(read)
    # if USE_LAST_MESSAGE_ID:
    #     database.set_last_message(last_msg_id, self.jid)

def get_user_data(uid, target_uid, fields=None):
    logger.debug('user api: sending user data for %s' % uid)
    fields = fields or ["screen_name"]
    args = {"fields": ",".join(fields), "user_ids": target_uid}
    m = "users.get"
    data = method(m, uid, args)
    print 'User data:'
    print data
    if data:
        data = data[0]
        data["name"] = escape_name("", u"%s %s" % (data["first_name"], data["last_name"]))
        del data["first_name"], data["last_name"]
    else:
        data = {}
        for key in fields:
            data[key] = "Unknown error when trying to get user data. We're so sorry."
    return data

def send_message(jid, body, recipient_uid, m_type="user_id"):
    logger.debug('user api: message to %s' % recipient_uid)
    method_name = "messages.send"
    method_values = {m_type: recipient_uid, "message": body, "type": 0}
    # try:
    update_last_activity(jid)
    return method(method_name, jid, method_values)
    # except Exception as e:
    #     logger.error('messages.send: %s' % e)
    #     dump_crash("messages.send")
    #     return False

def send_init_presence(gateway, jid):
    """
    Sends initial presences to user about friends and transport
    @type jid: str
    @type gateway: Gateway
    @param gateway: Gateway object
    @param jid: user jid
    @return: None
    """

    friends = database.get_friends(jid)

    assert isinstance(friends, dict)

    # friends = get_friends(jid)
    # TODO: Check friend list relevance
    logger.debug("user api: sending initial status to %s (friends %s)" % \
                 (jid, "exist" if friends else "empty"))

    # sending friends presence
    for friend_uid in friends:
        friend = friends[friend_uid]
        if not friend['online']:
            continue
        send_presence(gateway, jid, jid_from_uid(friend_uid), nick=friend['name'])

    # sending transport presence
    send_presence(gateway, jid, TRANSPORT_ID, nick=IDENTIFIER["name"])



def delete_user(jid, roster=False):
    logger.debug("user api: delete_user %s" % jid)

    database.remove_user(jid)
    friends = database.get_friends(jid)

    if roster and friends:
        logger.debug("user api: removing %s roster" % jid)
        for friend_id in friends:
            friend_jid = jid_from_uid(friend_id)
            send_presence(jid, friend_jid, "unsubscribe")
            send_presence(jid, friend_jid, "unsubscribed")
        database.set_offline(jid)

    database.remove_user(jid)
    database.remove_online_user(jid)

def update_friends(gateway, jid):
    friends_vk = get_friends(jid)
    friends_db = database.get_friends(jid)

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

    roster_subscribe(gateway, jid, subscriptions)

    for uid, status in update_status_dict.iteritems():
        send_presence(gateway, jid, uid, status)

    database.set_friends(jid, friends_vk)


def is_timed_out(jid):
    now = time.time()

    last_activity = database.get_last_activity(jid)

    # logger.debug('last activity for %s is %s' % (jid, last_activity))
    # logger.debug('now is %s' % now)

    # last_update = database.get_last_update(jid)

    user_inactive = (now - last_activity) > ACTIVE_TIMEOUT
    # roster_timeout = (now - last_update) > ROSTER_TIMEOUT

    return user_inactive

def initialize(gateway, jid, force=False, send=True):
    logger.debug("user api: called init for user %s" % jid)
    friends = get_friends(jid)
    database.set_friends(jid, friends)
    # roster_set = database.is_roster_set()

    if friends:
        logger.debug("user api: subscribing friends for %s" % jid)
        # roster_subscribe()
        roster_subscribe(gateway, jid, friends)
        logger.debug('SET FRIENDS!')
    if send:
        send_init_presence(gateway, jid)


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

def connect(gateway, jid, token):
    logger.debug("user api: connecting %s" % jid)
    # vk = VKLogin(gateway, token, jid)

    if not token:
        raise AuthenticationException('no token for %s' % jid)

    # logger.debug("user api: vk api initialized")
    try:
        logger.debug('user api: trying to auth with token')
        database.set_token(jid, token)
        login_api.check_token(gateway, jid, token)
        logger.debug("user api: authenticated %s" % jid)
    except CaptchaNeeded:
        logger.debug("user api: captcha needed for %s" % jid)
        roster_subscribe(gateway, jid)
        raise NotImplementedError('Captcha')
        # self.vk.captcha_challenge()
        # return True
    except TokenError as token_error:
        if token_error.message == "User authorization failed: user revoke access for this token.":
            logger.critical("user api: %s" % token_error.message)
            delete_user(jid)
        elif token_error.message == "User authorization failed: invalid access_token.":
            msg_send(gateway.component, jid,
                     token_error.message + " Please, register again", TRANSPORT_ID)
        raise AuthenticationException('invalid token')
    # except Exception as e:
    #     # TODO: We can crash there
    #     logger.debug('Auth failed: %s' % e)
    #     raise
    #     # dump_crash("TUser.Connect")
    #     # return False

    logger.debug("user api: updating db for %s" % jid)
    if not database.is_user(jid):
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
    database.set_online(jid)
    database.set_last_activity_now(jid)

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