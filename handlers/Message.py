# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

import library.xmpp as xmpp
import re
import config
import logging
import time
import pprint

from sender import stanza_send
# from library.stext import _
import library.vkapi as api

from handler import Handler
from hashers import get_hash
from config import WATCHER_LIST, TRANSPORT_ID

logger = logging.getLogger("vk4xmpp")

escape_name = re.compile(u"[^-0-9a-zа-яёë\._\'\ ґїє]", re.IGNORECASE | re.UNICODE | re.DOTALL).sub
escape_message = re.compile("|".join(config.BANNED_CHARS)).sub


def msg_send(cl, jid_to, body, jid_from, timestamp=None):
    logger.debug('msg_send %s -> %s' % (jid_from, jid_to))
    msg = xmpp.Message(jid_to, body, "chat", frm=jid_from)

    if timestamp:
        timestamp = time.gmtime(timestamp)
        msg.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))

    stanza_send(cl, msg)


msg_sort = lambda b_r, b_a: b_r["date"] - b_a["date"]

def msg_extract(msg):
    """
    Extracts message attributes into dictionary
    """
    msg_type = msg.getType()
    msg_body = msg.getBody()
    jid_to = msg.getTo()
    jid_to_str = jid_to.getStripped()
    jid_from = msg.getFrom()
    jid_from_str = jid_from.getStripped()

    return {'type': msg_type, 'body': msg_body, 'jid_to': jid_to,
            'jid_to_str': jid_to_str, 'jid_from': jid_from,
            'jid_from_str': jid_from_str
            }


def get_answer(message, jid_from, jid_to):
    logger.debug('msg_recieved from %s to %s' % (jid_from, jid_to))

    if not message.getTag("request"):
        return None

    m_id = message.getID()

    answer = xmpp.Message(jid_from)
    answer.setFrom(jid_to)
    answer.setID(m_id)

    tag = answer.setTag("received", namespace="urn:xmpp:receipts")
    tag.setAttr("id", m_id)

    return answer


class MessageHandler(Handler):
    def __init__(self, gateway):
        super(MessageHandler, self).__init__(gateway)

    def captcha_accept(self, cl, args, jid_to, jid_from_str):
        logger.debug('captcha accept from %s' % jid_from_str)

        if not args:
            return

        # GLOBAL LIST USAGE
        # CLIENT
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
                answer = "Captcha valid."
                presence = xmpp.protocol.Presence(jid_from_str, frm=config.TRANSPORT_ID)
                presence.setStatus("") # is it needed?
                presence.setShow("available")
                self.gateway.send(presence)
                client.try_again()
            else:
                answer = "Captcha invalid."
        else:
            answer = "Not now. Ok?"
        if answer:
            msg_send(cl, jid_from_str, answer, jid_to)

    def handle(self, cl, msg):

        m = msg_extract(msg)
        msg_body = m['body']
        jid_to = m['jid_to']
        jid_to_str = m['jid_to_str']
        jid_from = m['jid_from']
        jid_from_str = m['jid_from_str']

        logger.debug('message_handler handling: %s (%s->%s)' % (get_hash(msg_body), jid_from_str, jid_to_str))
        pprint.pprint(m)
        # TODO: Remove debug


        # if not is_client(jid)
        if jid_from_str not in self.gateway.clients or m['type'] != "chat":
            logger.debug('client %s not in list')
            return

        # GLOBAL LIST USAGE
        # client = get_client(jid)
        # if not client:
        #   return
        client = self.gateway.clients[jid_from_str]

        if not msg_body:
            return

        answer = None

        # message is going to transport id
        if jid_to == TRANSPORT_ID:
            logger.debug('message to transport_id')
            msg_raw = msg_body.split(None, 1)
            if len(msg_raw) > 1:
                text, args = msg_raw
                args = args.strip()
                if text == "!captcha" and args:
                    self.captcha_accept(cl, args, jid_to, jid_from_str)
                    answer = get_answer(msg, jid_from, jid_to)
                # TODO: evaluate and others
        else:
            logger.debug('message to user')
            uid = jid_to.getNode()

            # CLIENT FROM GLOBAL LIST USAGE
            vk_msg = client.msg(msg_body, uid)

            if vk_msg:
                answer = get_answer(msg, jid_from, jid_to)
        if answer:
            stanza_send(cl, answer)
        # for func in self.gateway.group_handlers:
        #     func(msg)


def watcher_msg(component, text):
    for jid in WATCHER_LIST:
        msg_send(component, jid, text, TRANSPORT_ID)

def get_handler(gateway):
    return MessageHandler(gateway).handle