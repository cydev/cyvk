# coding: utf-8
from __future__ import unicode_literals
from datetime import datetime

import compat
from api.vkapi import get_user_data
from messaging.attachments import parse_attachments
from parsing import escape, sorting
from config import MAXIMUM_FORWARD_DEPTH

_logger = compat.get_logger()


def parse_forwarded_messages(jid, msg, depth=0):
    body = ''

    if 'fwd_messages' not in msg:
        return body

    _logger.debug('forwarded messages for %s' % jid)

    body += '\nForward messages:'

    for fwd in sorted(msg['fwd_messages'], sorting):
        id_from = fwd['uid']
        date = fwd['date']
        fwd_body = escape('', compat.html_unespace(fwd['body']))
        date = datetime.fromtimestamp(date).strftime('%d.%m.%Y %H:%M:%S')
        name = get_user_data(jid, id_from)["name"]
        body += "\n[%s] <%s> %s" % (date, name, fwd_body)
        body += parse_attachments(jid, fwd)

        if depth < MAXIMUM_FORWARD_DEPTH:
            body += parse_forwarded_messages(jid, fwd, depth + 1)

    return body