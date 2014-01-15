# coding: utf-8

from datetime import datetime
from parsers import attachments
from messaging import escape_message, sort_message
from library.webtools import unescape
import user as user_api

from config import MAXIMUM_FORWARD_DEPTH

import logging

logger = logging.getLogger("vk4xmpp")


def parse_forwarded_messages(jid, msg, depth=0):
    body = ""

    if "fwd_messages" not in msg:
        return body

    logger.debug('forwarded messages for %s' % jid)

    body += "\nForward messages:"

    for fwd in sorted(msg["fwd_messages"], sort_message):

        id_from = fwd["uid"]
        date = fwd["date"]
        fwd_body = escape_message("", unescape(fwd["body"]))
        date = datetime.fromtimestamp(date).strftime("%d.%m.%Y %H:%M:%S")
        # name = user.get_user_data(id_from)["name"]
        name = user_api.get_user_data(jid, id_from)["name"]

        body += "\n[%s] <%s> %s" % (date, name, fwd_body)
        body += attachments.parse_attachments(jid, fwd)

        if depth < MAXIMUM_FORWARD_DEPTH:
            body += parse_forwarded_messages(jid, fwd, depth + 1)

    return body