# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

import logging

import xmpp as xmpp
import user as user_api
from sender import stanza_send
from handler import Handler
from hashers import get_hash
from config import TRANSPORT_ID
import database
from messaging import extract_message
from captcha import captcha_accept
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

    def handle(self, cl, msg):

        m = extract_message(msg)
        msg_body = m['body']

        if not msg_body:
            return

        jid_to = m['jid_to']
        jid_to_str = m['jid_to_str']
        jid_from = m['jid_from']
        jid_from_str = m['jid_from_str']

        jid = unicode(jid_from_str)

        logger.debug('message_handler handling: %s (%s->%s)' % (get_hash(msg_body), jid_from_str, jid_to_str))

        if not database.is_client(jid) or m['type'] != "chat":
            logger.debug('client %s not in list' % jid)

        answer = None

        if jid_to == TRANSPORT_ID:
            logger.debug('message to transport_id')
            msg_raw = msg_body.split(None, 1)
            if len(msg_raw) > 1:
                text, args = msg_raw
                args = args.strip()
                if text == "!captcha" and args:
                    captcha_accept(args, jid_to, jid_from_str)
                    answer = get_answer(msg, jid_from, jid_to)
                # TODO: evaluate and others
        else:
            uid = unicode(friends.get_friend_uid(jid_to.getNode()))
            logger.debug('message to user (%s->%s)' % (jid, uid))
            if user_api.send_message(jid, msg_body, uid):
                answer = get_answer(msg, jid_from, jid_to)
        if answer:
            stanza_send(cl, answer)

        # TODO: Group handlers


def get_handler():
    return MessageHandler().handle

