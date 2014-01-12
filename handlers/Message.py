# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

import library.xmpp as xmpp
import re
import config
import logging
import time

from sender import Sender
from library.writer import returnExc
from library.stext import _
import library.vkapi as api

from handler import Handler

from config import EVAL_JID, WATCHER_LIST, TRANSPORT_ID

logger = logging.getLogger("vk4xmpp")

escape_name = re.compile(u"[^-0-9a-zа-яёë\._\'\ ґїє]", re.IGNORECASE | re.UNICODE | re.DOTALL).sub
escape_message = re.compile("|".join(config.BANNED_CHARS)).sub


def msg_send(cl, jid_to, body, jid_from, timestamp=0):
    msg = xmpp.Message(jid_to, body, "chat", frm=jid_from)
    if timestamp:
        timestamp = time.gmtime(timestamp)
        msg.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))
    Sender(cl, msg)


msg_sort = lambda Br, Ba: Br["date"] - Ba["date"]


def msg_recieved(msg, jid_from, jid_to):
    if msg.getTag("request"):
        answer = xmpp.Message(jid_from)
        tag = answer.setTag("received", namespace="urn:xmpp:receipts")
        tag.setAttr("id", msg.getID())
        answer.setFrom(jid_to)
        answer.setID(msg.getID())
        return answer


class MessageHandler(Handler):
    def __init__(self, gateway):
        super(MessageHandler, self).__init__(gateway)

    def captcha_accept(self, cl, args, jid_to, jid_from_str):
        if args:
            client = self.clients[jid_from_str]
            if client.vk.engine.captcha:
                logger.debug("user %s called captcha challenge" % jid_from_str)
                client.vk.engine.captcha["key"] = args
                retry = False
                try:
                    logger.debug("retrying for user %s" % jid_from_str)
                    retry = client.vk.engine.retry()
                except api.CaptchaNeeded:
                    logger.error("retry for user %s failed!" % jid_from_str)
                    client.vk.captcha_challenge()
                if retry:
                    logger.debug("retry for user %s OK" % jid_from_str)
                    answer = _("Captcha valid.")
                    presence = xmpp.protocol.Presence(jid_from_str, frm=config.TRANSPORT_ID)
                    presence.setStatus("") # is it needed?
                    presence.setShow("available")
                    self.gateway.send(presence)
                    client.try_again()
                else:
                    answer = _("Captcha invalid.")
            else:
                answer = _("Not now. Ok?")
            if answer:
                msg_send(cl, jid_from_str, answer, jid_to)

    def handle(self, cl, msg):
        logger.debug('Message: %s' % msg)
        msg_type = msg.getType()
        msg_body = msg.getBody()
        jid_to = msg.getTo()
        # jid_to_str = jid_to.getStripped()
        jid_from = msg.getFrom()
        jid_from_str = jid_from.getStripped()
        logger.debug('"%s" to %s' % (msg_body, jid_to))
        client = None
        if jid_from_str in self.gateway.clients and msg_type == "chat":
            client = self.gateway.clients[jid_from_str]
        if client and msg_body:
            answer = None
            if jid_to == config.TRANSPORT_ID:
                raw = msg_body.split(None, 1)
                if len(raw) > 1:
                    text, args = raw
                    args = args.strip()
                    if text == "!captcha" and args:
                        self.captcha_accept(cl, args, jid_to, jid_from_str)
                        answer = msg_recieved(msg, jid_from, jid_to)
                    elif text == "!eval" and args and jid_from_str == EVAL_JID:
                        try:
                            result = unicode(eval(args))
                        except:
                            result = returnExc()
                        msg_send(cl, jid_from_str, result, jid_to)
                    elif text == "!exec" and jid_from_str == EVAL_JID:
                        try:
                            exec(unicode(args + "\n"), globals());
                            result = "Done."
                        except:
                            result = returnExc()
                        msg_send(cl, jid_from_str, result, jid_to)
            else:
                uid = jid_to.getNode()
                vk_msg = client.msg(msg_body, uid)
                if vk_msg:
                    answer = msg_recieved(msg, jid_from, jid_to)
            if answer:
                Sender(cl, answer)
        for func in self.gateway.group_handlers:
            func(msg)


def watcher_msg(component, text):
    for jid in WATCHER_LIST:
        msg_send(component, jid, text, TRANSPORT_ID)

def get_handler(gateway):
    return MessageHandler(gateway).handle