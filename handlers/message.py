# coding: utf-8
from __future__ import unicode_literals

import compat
from cystanza.stanza import ChatMessage, Answer
from parallel import realtime
from parallel.stanzas import push
from parallel.updates import send_message
from config import TRANSPORT_ID
import friends

_logger = compat.get_logger()


def handler(m):
    """
    :type m: ChatMessage
    """
    assert isinstance(m, ChatMessage)

    jid = m.origin

    _logger.debug('message_handler handling: (%s->%s)' % (jid, m.destination))

    if jid == TRANSPORT_ID:
        return _logger.error('not implemented - message to watcher')

    if not realtime.is_client(jid):
        _logger.debug('client %s not in list' % jid)

    if m.destination == TRANSPORT_ID:
        return _logger.error('not implemented - message to transport_id')

    uid = friends.get_friend_uid(m.destination)
    _logger.debug('message to user (%s->%s)' % (jid, uid))
    send_message(jid, m.text, uid)

    if m.requests_answer:
        answer = Answer(m.destination, jid, message_id=m.message_id)
        push(answer)

