# coding: utf-8
from __future__ import unicode_literals

import compat
from parallel import realtime
from parallel.stanzas import push
from parallel.updates import send_message
from config import TRANSPORT_ID
from transport.processing import Message
import friends
import transport.messages

_logger = compat.get_logger()


def _get_answer(message, jid_from, jid_to):
    _logger.debug('msg_received from %s to %s' % (jid_from, jid_to))
    return transport.messages.get_answer_stanza(jid_from, jid_to, message)


def handler(_, stanza):
    m = Message(stanza)

    if m.composing:
        return _logger.error('composing not implemented')

    if not m.body:
        return

    jid = m.jid_from

    _logger.debug('message_handler handling: (%s->%s)' % (m.jid_from, m.jid_to))

    if not realtime.is_client(jid) or m.msg_type != "chat":
        _logger.debug('client %s not in list' % jid)

    if m.jid_to == TRANSPORT_ID:
        return _logger.error('not implemented - message to transport_id')

    if m.jid_from == TRANSPORT_ID:
        return _logger.error('not implemented - message to watcher')

    uid = friends.get_friend_uid(m.jid_to)
    _logger.debug('message to user (%s->%s)' % (jid, uid))

    # TODO: replace by something less verbose
    if not send_message(jid, m.body, uid):
        return

    answer = _get_answer(stanza, m.jid_from, m.jid_to)

    if answer:
        push(answer)

