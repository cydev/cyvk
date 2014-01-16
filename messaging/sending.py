import time
import logging

from config import WATCHER_LIST, TRANSPORT_ID
from transport.stanza_queue import push
from xmpp import Message


logger = logging.getLogger("vk4xmpp")


def send(jid_to, body, jid_from, timestamp=None):
    logger.debug('sending message %s -> %s' % (jid_from, jid_to))

    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)
    assert isinstance(body, unicode)

    message = Message(jid_to, body, "chat", frm=jid_from)

    if timestamp:
        timestamp = time.gmtime(timestamp)
        message.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))

    push(message)


def send_typing_status(jid_to, jid_from):
    logger.debug('typing %s -> %s' % (jid_from, jid_to))

    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)

    message = Message(jid_to, typ='chat', frm=jid_from)
    message.setTag('composing', namespace='http://jabber.org/protocol/chatstates')

    push(message)


def send_to_watcher(text):
    """
    Send message to watcher
    @type text: unicode
    @param text: unicode message body
    """

    assert isinstance(text, unicode)

    logger.debug('sending message %s to watchers' % text)

    for jid in WATCHER_LIST:
        send(jid, text, TRANSPORT_ID)