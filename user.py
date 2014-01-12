import signal
import socket
import threading
from hashlib import sha1
from config import *
import re

import logging
import sys
import os
import time

from vklogin import VKLogin
from library.itypes import Database
from config import DB_FILE

import logging
from run import run_thread
from library.writer import dump_crash
from handlers.message import msg_send, msg_sort, escape_name, escape_message
import library.vkapi as api
import library.webtools as webtools
from vk2xmpp import vk2xmpp
import library.xmpp as xmpp
from sender import stanza_send
from library.stext import _ as _

from run import f_apply

logger = logging.getLogger("vk4xmpp")
import library.stext as stext


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
        self.jid_from = source
        self.resources = []
        self.chat_users = {}
        self.user_id = None
        self.vk = VKLogin(self.username, self.password, self.jid_from)
        logger.debug("TUSER init %s" % self.jid_from)

        # TODO: Semaphore
        # TODO: Abstract
        # TODO: Postgres/Redis
        with Database(DB_FILE) as db:
            db("SELECT * FROM users WHERE jid=?", (self.jid_from,))
            desc = db.fetchone()
            if not desc:
                return
            if not self.token or not self.password:
                logger.debug("TUser: %s exists in db. Using it." % self.jid_from)
                self.exists_id_db = True
                self.jid_from, self.username, self.token, self.last_msg_id, self.roster_set = desc
            elif self.password or self.token:
                logger.debug("TUser: %s exists in db. Will be deleted." % self.jid_from)
                run_thread(self.delete_user)

    def __str__(self):
        return '<TUser %s:%s>' % (self.username, self.user_id)

    def delete_user(self, roster=False):
        logger.debug("tUser: deleting user %s from db." % self.jid_from)

        # TODO: Abstract
        with Database(DB_FILE) as db:
            db("DELETE FROM users WHERE jid=?", (self.jid_from,))
            db.commit()
        self.exists_id_db = False

        if roster and self.friends:
            logger.debug("tUser: deleting me from %s roster" % self.jid_from)
            for friend_id in self.friends.keys():
                jid = vk2xmpp(friend_id)
                self.send_presence(self.jid_from, jid, "unsubscribe")
                self.send_presence(self.jid_from, jid, "unsubscribed")
            self.vk.is_online = False

        if self.jid_from in self.gateway.clients:
            del self.gateway.clients[self.jid_from]
            try:
                self.gateway.update_transports_list(self, False)
            except NameError:
                pass

    # noinspection PyShadowingNames
    def msg(self, body, uid, m_type="user_id"):
        logger.debug('TUser: msg to %s' % uid)

        # noinspection PyBroadException
        try:
            self.last_activity = time.time()
            msg = self.vk.method("messages.send", {m_type: uid, "message": body, "type": 0})
        except:
            dump_crash("messages.send")
            msg = False
        return msg

    def connect(self):
        logger.debug("tUser: connecting %s" % self.jid_from)
        self.auth = False
        # noinspection PyBroadException
        try:
            self.auth = self.vk.auth(self.token)
            logger.debug("tUser: auth=%s for %s" % (self.auth, self.jid_from))
        except api.CaptchaNeeded:
            self.roster_subscribe()
            self.vk.captcha_challenge()
            return True
        except api.TokenError as token_error:
            if token_error.message == "User authorization failed: user revoke access for this token.":
                logger.critical("tUser: %s" % token_error.message)
                self.delete_user()
            elif token_error.message == "User authorization failed: invalid access_token.":
                msg_send(self.gateway.component, self.jid_from, stext._(token_error.message + " Please, register again"), TRANSPORT_ID)
            self.vk.is_online = False
        except:
            dump_crash("tUser.Connect")
            return False

        if self.auth and self.vk.get_token():
            logger.debug("tUser: updating db for %s because auth done " % self.jid_from)
            if not self.exists_id_db:
                # TODO: Semaphore
                with Database(DB_FILE) as db:
                    db("INSERT INTO users VALUES (?,?,?,?,?)", (self.jid_from, self.username,
                                                                self.vk.get_token(), self.last_msg_id, self.roster_set))
            elif self.password:
                with Database(DB_FILE) as db:
                    db("UPDATE users SET token=? WHERE jid=?", (self.vk.get_token(), self.jid_from))
            try:
                _ = self.vk.method("users.get")
                self.user_id = _[0]["uid"]
            except (KeyError, TypeError):
                logger.error("tUser: could not recieve user id. JSON: %s" % str(_))
                self.user_id = 0

            self.gateway.jid_to_id[self.user_id] = self.jid_from
            self.friends = self.vk.get_friends()
            self.vk.is_online = True
        if not USE_LAST_MESSAGE_ID:
            self.last_msg_id = 0
        return self.vk.is_online

    def init(self, force=False, send=True):
        logger.debug("tUser: called init for user %s" % self.jid_from)
        self.friends = self.vk.get_friends()
        if self.friends and not self.roster_set or force:
            logger.debug("tUser: calling subscribe with force:%s for %s" % (force, self.jid_from))
            self.roster_subscribe(self.friends)
        if send: self.send_init_presence()

    def send_presence(self, target, jidFrom, pType=None, nick=None, reason=None):
        presence = xmpp.Presence(target, pType, frm=jidFrom, status=reason)
        if nick:
            presence.setTag("nick", namespace=xmpp.NS_NICK)
            presence.setTagData("nick", nick)
        self.gateway.send(presence)

    def send_init_presence(self):
        self.friends = self.vk.get_friends()
        # too too bad way to do it again. But it's a guarantee of the availability of friends.
        logger.debug("TUser: sending init presence to %s (friends %s)" % \
                     (self.jid_from, "exists" if self.friends else "empty"))
        for uid, value in self.friends.iteritems():
            if value["online"]:
                self.send_presence(self.jid_from, vk2xmpp(uid), None, value["name"])
        self.send_presence(self.jid_from, TRANSPORT_ID, None, IDENTIFIER["name"])

    def send_out_presence(self, target, reason=None):
        # TODO: Why this needed?
        p_type = "unavailable"
        logger.debug("TUser: sending out presence to %s" % self.jid_from)
        for uid in self.friends.keys() + [TRANSPORT_ID]:
            self.send_presence(target, vk2xmpp(uid), "unavailable", reason=reason)

    def roster_subscribe(self, dist=None):
        dist = dist or {}
        for uid, value in dist.iteritems():
            self.send_presence(self.jid_from, vk2xmpp(uid), "subscribe", value["name"])
        self.send_presence(self.jid_from, TRANSPORT_ID, "subscribe", IDENTIFIER["name"])

        if dist:
            self.roster_set = True
            # TODO: Semaphore
            with Database(DB_FILE) as db:
                db("UPDATE users SET rosterSet=? WHERE jid=?",
                   (self.roster_set, self.jid_from))

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
        logger.debug('TUser: send_messages for %s' % self.user_id)
        messages = self.vk.get_messages(200, self.last_msg_id if USE_LAST_MESSAGE_ID else 0)

        if not messages:
            return

        messages = messages[1:]
        messages = sorted(messages, msg_sort)

        if not messages:
            return

        read = list()
        self.last_msg_id = messages[-1]["mid"]
        for message in messages:
            read.append(str(message["mid"]))
            from_jid = vk2xmpp(message["uid"])
            body = webtools.unescape(message["body"])
            # iter = handlers["msg01"]
            for func in self.gateway.handlers:
                # noinspection PyBroadException
                # TODO: Maybe too broad?
                try:
                    result = func(self, message)
                except Exception as e:
                    result = None
                    logger.error('Error while processing handlers %s' % e)
                    dump_crash("handle.%s" % func.func_name)
                    raise e
                if result is None:
                    for func in self.gateway.handlers:
                        f_apply(func, (self, message))
                    break
                else:
                    body += result
            else:
                msg_send(self.gateway.component, self.jid_from, escape_message("", body), from_jid, message["date"])
        self.vk.msg_mark_as_read(read)
        if USE_LAST_MESSAGE_ID:
            # TODO: Semaphore
            with Database(DB_FILE) as db:
                db("UPDATE users SET lastMsgID=? WHERE jid=?", (self.last_msg_id, self.jid_from))

    def try_again(self):
        logger.debug("calling reauth for user %s" % self.jid_from)
        try:
            if not self.vk.is_online:
                self.connect()
            self.init(True)
        except:
            dump_crash("tryAgain")