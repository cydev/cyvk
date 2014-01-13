# coding=utf-8
__author__ = 'ernado'
import logging
import time
import re

import library.xmpp as xmpp
from sender import stanza_send
from config import BANNED_CHARS, WATCHER_LIST, TRANSPORT_ID

logger = logging.getLogger("vk4xmpp")

def msg_send(cl, jid_to, body, jid_from, timestamp=None):
    logger.debug('msg_send %s -> %s' % (jid_from, jid_to))
    msg = xmpp.Message(jid_to, body, "chat", frm=jid_from)

    if timestamp:
        timestamp = time.gmtime(timestamp)
        msg.setTimestamp(time.strftime("%Y%m%dT%H:%M:%S", timestamp))

    stanza_send(cl, msg)

escape_name = re.compile(u"[^-0-9a-zа-яёë\._\'\ ґїє]", re.IGNORECASE | re.UNICODE | re.DOTALL).sub
escape_message = re.compile("|".join(BANNED_CHARS)).sub


msg_sort = lambda b_r, b_a: b_r["date"] - b_a["date"]

def msg_extract(msg):
    """
    Extracts message attributes into dictionary
    """
    msg_type = msg.getType()
    msg_body = msg.getBody()
    jid_to = msg.getTo()
    jid_to_str = jid_to.getStripped()
    jid_from = msg.getFrom()
    jid_from_str = jid_from.getStripped()

    return {'type': msg_type, 'body': msg_body, 'jid_to': jid_to,
            'jid_to_str': jid_to_str, 'jid_from': jid_from,
            'jid_from_str': jid_from_str
            }

def watcher_msg(component, text):
    for jid in WATCHER_LIST:
        msg_send(component, jid, text, TRANSPORT_ID)
