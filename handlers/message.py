# coding: utf-8
from __future__ import unicode_literals

import logging
from parallel import realtime
from parallel.stanzas import push
from parallel.updates import send_message

from config import TRANSPORT_ID
from transport.processing import Message

import friends
import transport.messages

logger = logging.getLogger("cyvk")


def _get_answer(message, jid_from, jid_to):
    logger.debug('msg_received from %s to %s' % (jid_from, jid_to))
    return transport.messages.get_answer_stanza(jid_from, jid_to, message)


def _handle(_, stanza):
    m = Message(stanza)

    if m.composing:
        return logger.error('composing not implemented')

    if not m.body:
        return

    jid = m.jid_from

    logger.debug('message_handler handling: (%s->%s)' % (m.jid_from, m.jid_to))

    if not realtime.is_client(jid) or m.msg_type != "chat":
        logger.debug('client %s not in list' % jid)

    if m.jid_to == TRANSPORT_ID:
        return logger.error('not implemented - message to transport_id')

    if m.jid_from == TRANSPORT_ID:
        return logger.error('not implemented - message to watcher')

    uid = friends.get_friend_uid(m.jid_to)
    logger.debug('message to user (%s->%s)' % (jid, uid))

    # TODO: replace by something less verbose
    if not send_message(jid, m.body, uid):
        return

    answer = _get_answer(stanza, m.jid_from, m.jid_to)

    if answer:
        push(answer)


def get_handler():
    return _handle

