# coding: utf-8

from __future__ import unicode_literals

import logging
from parallel import realtime
from parallel.stanzas import push
from parallel.updates import send_message
from handlers.handler import Handler
from hashers import get_hash

from config import TRANSPORT_ID
from transport.processing import Message

import friends
import transport.messages

logger = logging.getLogger("cyvk")


def get_answer(message, jid_from, jid_to):
    logger.debug('msg_received from %s to %s' % (jid_from, jid_to))
    return transport.messages.get_answer_stanza(jid_from, jid_to, message)


class MessageHandler(Handler):
    def handle(self, _, stanza):

        logger.warning('message: %s' % stanza)
        m = Message(stanza)

        if m.composing:
            logger.error('composing not implemented')

        if not m.body:
            return
        jid = m.jid_from

        logger.debug('message_handler handling: %s (%s->%s)' % (get_hash(m.body), m.jid_from, m.jid_to))

        if not realtime.is_client(jid) or m.msg_type != "chat":
            logger.debug('client %s not in list' % jid)

        if m.jid_to == TRANSPORT_ID:
            return logger.error('message to transport_id')

        if m.jid_from == TRANSPORT_ID:
            return logger.error('not implemented - messages to watcher')

        uid = unicode(friends.get_friend_uid(m.jid_to))
        logger.debug('message to user (%s->%s)' % (jid, uid))
        if not send_message(jid, m.body, uid):
            return
        answer = get_answer(stanza, m.jid_from, m.jid_to)

        if answer:
            push(answer)


def get_handler():
    return MessageHandler().handle

