import time
import logging

from config import TRANSPORT_ID, USE_LAST_MESSAGE_ID, IDENTIFIER
from vklogin import VKLogin
from run import run_thread
from library.writer import dump_crash
from messaging import msg_send, msg_sort, escape_name, escape_message
import library.vkapi as api
import library.webtools as webtools
from vklogin import get_messages, mark_messages_as_read
from vk2xmpp import parse
import library.xmpp as xmpp
from errors import CaptchaNeeded, TokenError

from library.vkapi import method

logger = logging.getLogger("vk4xmpp")
import library.stext as stext

import database

def set_online(user):
    m = "account.setOnline"
    method(m, user)


def update_last_activity(uid):
    logger.debug('Updating last activity')
    database.set_last_activity(uid, time.time())

def get_friends(jid, fields=None):
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
    def __init__(self, gateway, data=(), source=""):
        self.password = None
        self.gateway = gateway
        if data:
            # noinspection PyTupleAssignmentBalance
            self.username, self.password = data
        self.friends = {}
        self.auth = None
        self.token = None
        self.last_msg_id = None
        self.roster_set = None
        self.exists_id_db = None
        self.last_status = None
        self.last_activity = time.time()
        self.last_update = time.time()
        self.jid = source
        self.resources = []
        self.chat_users = {}
        self.user_id = None
        self.vk = VKLogin(self.username, self.password, self.jid)

        logger.debug("TUSER init %s" % self.jid)
        desc = database.get_description(self.jid)
        if not desc:
            return

        if not self.token or not self.password:
            logger.debug("TUser: %s exists in db. Using it." % self.jid)
            self.exists_id_db = True
            self.jid, self.username, self.token, self.last_msg_id, self.roster_set = desc
        elif self.password or self.token:
            logger.debug("TUser: %s exists in db. Will be deleted." % self.jid)
            run_thread(self.delete_user)

    def __repr__(self):
        return '<TUser %s>' % self.jid

    def delete_user(self, roster=False):
        logger.debug("TUser: delete_user %s" % self.jid)

        database.remove_user(self.jid)
        self.exists_id_db = False

        if roster and self.friends:
            logger.debug("TUser: removing %s roster" % self.jid)
            for friend_id in self.friends:
                jid = parse(friend_id)
                self.send_presence(self.jid, jid, "unsubscribe")
                self.send_presence(self.jid, jid, "unsubscribed")
            self.vk.is_online = False

        if self.jid in self.gateway.clients:
            del self.gateway.clients[self.jid]
            try:
                self.gateway.remove_user(self.jid)
            except NameError as e:
                logger.debug(e)

    # noinspection PyShadowingNames
    def msg(self, body, recipient_uid, m_type="user_id"):
        logger.debug('TUser: msg to %s' % recipient_uid)
        method_name = "messages.send"
        method_values = {m_type: recipient_uid, "message": body, "type": 0}
        # noinspection PyBroadException
        try:
            update_last_activity(self.jid)
            a = database.get_last_activity(self.jid)
            return method(method_name, self.jid, method_values)
            # msg = self.vk.method("messages.send", {m_type: uid, "message": body, "type": 0})
        except Exception as e:
            logger.error('messages.send: %s' % e)
            dump_crash("messages.send")
            return False

    def connect(self):
        jid = self.jid
        authenticated = False
        token = self.token
        gateway = self.gateway

        logger.debug("TUser: connecting %s" % jid)
        is_online = False
        # noinspection PyBroadException
        try:
            logger.debug('TUser: trying to auth with token %s' % token)
            authenticated = self.vk.auth(token)
            database.set_token(jid, token)
            logger.debug("TUser: auth=%s for %s" % (authenticated, jid))
        except CaptchaNeeded:
            logger.debug("TUser: captcha needed for %s" % jid)
            roster_subscribe(gateway, jid)
            self.vk.captcha_challenge()
            return True
        except TokenError as token_error:
            if token_error.message == "User authorization failed: user revoke access for this token.":
                logger.critical("TUser: %s" % token_error.message)
                self.delete_user()
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
            if not self.exists_id_db:
                database.add_user(self.jid, self.username, token, self.last_msg_id, self.roster_set)
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
        self.friends = get_friends(self.jid)
        if self.friends and not self.roster_set or force:
            logger.debug("TUser: calling subscribe with force:%s for %s" % (force, self.jid))
            self.roster_subscribe(self.friends)
        if send: self.send_init_presence()

    def send_presence(self, target, jid_from, p_type=None, nick=None, reason=None):
        logger.debug('sending presence for %s about %s' % (target, jid_from))
        presence = xmpp.Presence(target, p_type, frm=jid_from, status=reason)
        if nick:
            presence.setTag("nick", namespace=xmpp.NS_NICK)
            presence.setTagData("nick", nick)
        self.gateway.send(presence)

    def send_init_presence(self):
        self.friends = database.get_friends(self.jid)
        # too too bad way to do it again. But it's a guarantee of the availability of friends.
        logger.debug("TUser: sending init presence to %s (friends %s)" % \
                     (self.jid, "exists" if self.friends else "empty"))
        for uid, value in self.friends.iteritems():
            if value["online"]:
                self.send_presence(self.jid, parse(uid), None, value["name"])
        self.send_presence(self.jid, TRANSPORT_ID, None, IDENTIFIER["name"])

    def send_out_presence(self, target, reason=None):
        # TODO: Why this needed?
        p_type = "unavailable"
        logger.debug("TUser: sending out presence to %s" % self.jid)
        for uid in self.friends.keys() + [TRANSPORT_ID]:
            self.send_presence(target, parse(uid), p_type, reason=reason)

    def roster_subscribe(self, dist=None):
        dist = dist or {}
        for uid, value in dist.iteritems():
            self.send_presence(self.jid, parse(uid), "subscribe", value["name"])
        self.send_presence(self.jid, TRANSPORT_ID, "subscribe", IDENTIFIER["name"])

        if dist:
            self.roster_set = True
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
            from_jid = parse(message["uid"])
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

def send_presence(gateway, target, jid_from, p_type=None, nick=None, reason=None):
    logger.debug('sending presence for %s about %s' % (target, jid_from))
    presence = xmpp.Presence(target, p_type, frm=jid_from, status=reason)
    if nick:
        presence.setTag("nick", namespace=xmpp.NS_NICK)
        presence.setTagData("nick", nick)
    gateway.send(presence)

def roster_subscribe(gateway, jid, dist=None):
    """
    Subscribe user for jids in dist
    """
    logger.debug('roster_subscribe for %s' % jid)

    if not dist:
        send_presence(gateway, jid, TRANSPORT_ID, "subscribe", IDENTIFIER["name"])
        return

    for uid, value in dist.iteritems():
        send_presence(gateway, jid, parse(uid), "subscribe", value["name"])


def send_messages(gateway, jid):
    logger.debug('TUser: send_messages for %s' % jid)

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
        database.set_last_message(last_message, jid)

    for message in messages:
        read.append(str(message["mid"]))
        from_jid = parse(message["uid"])
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
    logger.debug('TUser: sending user data for %s' % uid)
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
    logger.debug('TUser: msg to %s' % recipient_uid)
    method_name = "messages.send"
    method_values = {m_type: recipient_uid, "message": body, "type": 0}
    # try:
    update_last_activity(jid)
    return method(method_name, jid, method_values)
    # except Exception as e:
    #     logger.error('messages.send: %s' % e)
    #     dump_crash("messages.send")
    #     return False