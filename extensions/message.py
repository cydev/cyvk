__author__ = 'ernado'

from attachments import parse_attachments
from forwarded_messages import parse_forwarded_messages
from geo import parse_geo

import pprint

import logging

logger = logging.getLogger("vk4xmpp")

mapping = {'geo': parse_geo, 'fwd_messages': parse_forwarded_messages, 'attachments': parse_attachments}

def parse_message(self, message):
    pprint.pprint(message)

    body = ""
    logger.debug('Parsing message')
    for k in mapping:
        if k in message:
            logger.debug('Found %s key, processing' % k)
            body += mapping[k](self, message)

    logger.debug('Message processed')
    return body