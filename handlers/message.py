# coding: utf-8

from __future__ import unicode_literals

import logging
from parallel import realtime
from parallel.stanzas import push
from parallel.updates import send_message
from handlers.handler import Handler
from hashers import get_hash

from config import TRANSPORT_ID
from transport.processing import from_stanza

import friends
import transport.messages

logger = logging.getLogger("cyvk")


def get_answer(message, jid_from, jid_to):
    logger.debug('msg_received from %s to %s' % (jid_from, jid_to))
    return transport.messages.get_answer_stanza(jid_from, jid_to, message)


class MessageHandler(Handler):
    def handle(self, _, stanza):

        logger.warning('message: %s' % stanza)
        m = from_stanza(stanza)
        body = m['body']

        if m['composing']:
            logger.error('composing not implemented')

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

        if jid_to == TRANSPORT_ID:
            return logger.debug('message to transport_id: %s' % body)

        if jid_from == TRANSPORT_ID:
            return logger.error('not implemented - messages to watcher')
        else:
            uid = unicode(friends.get_friend_uid(jid_to.getNode()))
            logger.debug('message to user (%s->%s)' % (jid, uid))
            if not send_message(jid, body, uid):
                return
        answer = get_answer(stanza, jid_from_str, jid_to_str)
        push(answer)


def get_handler():
    return MessageHandler().handle

