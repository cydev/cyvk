# coding=utf-8

from __future__ import unicode_literals
from xmpp.protocol import Protocol
import logging
logger = logging.getLogger("cyvk")


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
    composing = msg_type == 'chat' and msg.getTag('composing')

    return {'type': msg_type, 'body': msg_body, 'jid_to': jid_to,
            'jid_to_str': jid_to_str, 'jid_from': jid_from,
            'jid_from_str': jid_from_str, 'composing': composing}


