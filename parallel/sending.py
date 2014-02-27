from __future__ import unicode_literals
import time

from parallel.stanzas import push
from cystanza.stanza import ChatMessage
from compat import get_logger


_logger = get_logger()


def send(jid_to, body, jid_from, timestamp=None):
    _logger.debug('sending message %s -> %s' % (jid_from, jid_to))

    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)
    assert isinstance(body, unicode)

    if timestamp:
        timestamp = time.gmtime(timestamp)
        timestamp = time.strftime("%Y%m%dT%H:%M:%S", timestamp)

    message = ChatMessage(jid_from, jid_to, body, timestamp=timestamp)
    push(message)