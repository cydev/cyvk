from __future__ import unicode_literals
from messaging.attachments import parse_attachments
from forwarded_messages import parse_forwarded_messages
from geo import parse_geo
import compat

_logger = compat.get_logger()
_mapping = {'geo': parse_geo, 'fwd_messages': parse_forwarded_messages, 'attachments': parse_attachments}


def parse(jid, message):
    if not jid:
        raise ValueError('user is None')

    body = ''
    _logger.debug('parse_message for %s' % jid)
    for k in _mapping:
        if k in message:
            _logger.debug('found %s key, processing' % k)
            body += _mapping[k](jid, message)

    _logger.debug('parse_message for %s processed' % jid)
    return body