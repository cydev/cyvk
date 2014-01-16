# coding: utf-8

from datetime import datetime
import logging

from messaging.attachments import parse_attachments
from messaging.processing import escape, sorting
from transport import user as user_api
from api.webtools import unescape
from config import MAXIMUM_FORWARD_DEPTH


logger = logging.getLogger("vk4xmpp")


def parse_forwarded_messages(jid, msg, depth=0):
    body = ""

    if "fwd_messages" not in msg:
        return body

    logger.debug('forwarded messages for %s' % jid)

    body += "\nForward messages:"

    for fwd in sorted(msg["fwd_messages"], sorting):

        id_from = fwd["uid"]
        date = fwd["date"]
        fwd_body = escape("", unescape(fwd["body"]))
        date = datetime.fromtimestamp(date).strftime("%d.%m.%Y %H:%M:%S")
        # name = user.get_user_data(id_from)["name"]
        name = user_api.get_user_data(jid, id_from)["name"]

        body += "\n[%s] <%s> %s" % (date, name, fwd_body)
        body += parse_attachments(jid, fwd)

        if depth < MAXIMUM_FORWARD_DEPTH:
            body += parse_forwarded_messages(jid, fwd, depth + 1)

    return body