# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

# Cleaned by Ernado, Cydev

from datetime import datetime
from extensions import attachments
from messaging import escape_message, msg_sort
from library.webtools import unescape
import user as user_api

from config import MAXIMUM_FORWARD_DEPTH


def parse_forwarded_messages(user, msg, depth=0):
    body = ""

    if "fwd_messages" not in msg:
        return body

    body += "\nForward messages:"

    for fwd in sorted(msg["fwd_messages"], msg_sort):

        id_from = fwd["uid"]
        date = fwd["date"]
        fwd_body = escape_message("", unescape(fwd["body"]))
        date = datetime.fromtimestamp(date).strftime("%d.%m.%Y %H:%M:%S")
        name = user.get_user_data(id_from)["name"]
        # user_data = user_api.get_user_data(user.jid, id_from)

        body += "\n[%s] <%s> %s" % (date, name, fwd_body)
        body += attachments.parse_attachments(user, fwd)

        if depth < MAXIMUM_FORWARD_DEPTH:
            body += parse_forwarded_messages(user, fwd, depth + 1)

    return body