__author__ = 'ernado'

from messaging.attachments import parse_attachments
from forwarded_messages import parse_forwarded_messages
from geo import parse_geo
from hashers import get_hash

import logging

logger = logging.getLogger("vk4xmpp")

mapping = {'geo': parse_geo, 'fwd_messages': parse_forwarded_messages, 'attachments': parse_attachments}

def parse(jid, message):
    h = get_hash(message['body'])

    if not jid:
        raise ValueError('user is None')

    body = ""
    logger.debug('parse_message %s for %s' % (h, jid))
    for k in mapping:
        if k in message:
            logger.debug('found %s key, processing' % k)
            body += mapping[k](jid, message)

    logger.debug('parse_message %s processed' % h)
    return body