# coding=utf-8

from __future__ import unicode_literals

import logging
import re

from xmpp.protocol import Protocol
from config import BANNED_CHARS

logger = logging.getLogger("vk4xmpp")


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


