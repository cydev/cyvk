# coding=utf-8

from __future__ import unicode_literals

import logging
import time
import re
from realtime import queue_stanza

from xmpp.protocol import Message, Protocol
from config import BANNED_CHARS, WATCHER_LIST, TRANSPORT_ID
import database

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

    queue_stanza(message)

def send_typing_status(jid_to, jid_from):
    logger.debug('typing %s -> %s' % (jid_from, jid_to))

    assert isinstance(jid_to, unicode)
    assert isinstance(jid_from, unicode)

    message = Message(jid_to, typ='chat', frm=jid_from)
    message.setTag('composing', namespace='http://jabber.org/protocol/chatstates')

    queue_stanza(message)


escape_name = re.compile(u"[^-0-9a-zа-яёë\._\'\ ґїє]", re.IGNORECASE | re.UNICODE | re.DOTALL).sub
escape = re.compile("|".join(BANNED_CHARS)).sub


sorting = lambda b_r, b_a: b_r["date"] - b_a["date"]

def from_stanza(msg):
    """
    Extract message attributes from stanza into dictionary
    """

    assert isinstance(msg, Protocol)

    msg_type = msg.getType()
    msg_body = msg.getBody()
    jid_to = msg.getTo()
    jid_to_str = unicode(jid_to.getStripped())
    jid_from = msg.getFrom()
    jid_from_str = unicode(jid_from.getStripped())

    return {'type': msg_type, 'body': msg_body, 'jid_to': jid_to,
            'jid_to_str': jid_to_str, 'jid_from': jid_from,
            'jid_from_str': jid_from_str
            }

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
