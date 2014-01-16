# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

from __future__ import unicode_literals

import logging
from parallel import realtime
from transport import user as user_api

import xmpp as xmpp
from transport.handlers.handler import Handler
from hashers import get_hash
from config import TRANSPORT_ID
import messaging
from transport.captcha import captcha_accept
from transport.stanza_queue import push
import friends


logger = logging.getLogger("vk4xmpp")




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
    # def __init__(self, gateway):
    #     super(MessageHandler, self).__init__(gateway)

    def captcha_accept(self, args, jid_to, jid_from_str):
        captcha_accept(args, jid_to, jid_from_str)

    def handle(self, transport, stanza):

        m = messaging.from_stanza(stanza)
        body = m['body']

        if not body:
            return

        jid_to = m['jid_to']
        jid_to_str = m['jid_to_str']
        jid_from = m['jid_from']
        jid_from_str = m['jid_from_str']

        jid = unicode(jid_from_str)

        logger.debug('message_handler handling: %s (%s->%s)' % (get_hash(body), jid_from_str, jid_to_str))

        if not realtime.is_client(jid) or m['type'] != "chat":
            logger.debug('client %s not in list' % jid)

        answer = None

        if jid_to == TRANSPORT_ID:
            logger.debug('message to transport_id')
            msg_raw = body.split(None, 1)
            if len(msg_raw) > 1:
                text, args = msg_raw
                args = args.strip()
                if text == "!captcha" and args:
                    captcha_accept(args, jid_to, jid_from_str)
                    answer = get_answer(stanza, jid_from, jid_to)
                # TODO: evaluate and others
        if jid_from == TRANSPORT_ID:
            # logger.debug('sending message from transport to %s' % jid_to)
            # user_api.send_message(jid_to_str, body, jid_from_str)
            logger.error('not implemented - messages to watcher')
        else:
            uid = unicode(friends.get_friend_uid(jid_to.getNode()))
            logger.debug('message to user (%s->%s)' % (jid, uid))
            if user_api.send_message(jid, body, uid):
                answer = get_answer(stanza, jid_from, jid_to)
        if answer:
            push(answer)

        # TODO: Group handlers


def get_handler():
    return MessageHandler().handle

