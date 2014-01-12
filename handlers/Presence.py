# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

from library.writer import dump_crash
from config import TRANSPORT_ID, DB_FILE
from user import TUser
from handlers.message import msg_send, watcher_msg
from library.itypes import Database
from sender import stanza_send
import library.xmpp as xmpp
from library.stext import _
from vk2xmpp import vk2xmpp

import logging
logger = logging.getLogger("vk4xmpp")
from handler import Handler


class PresenceHandler(Handler):
    def __init__(self, gateway):
        super(PresenceHandler, self).__init__(gateway)

    def handle(self, cl, prs):
        p_type = prs.getType()
        jid_from = prs.getFrom()
        jid_to = prs.getTo()
        jid_from_str = jid_from.getStripped()
        jid_to_str = jid_to.getStripped()
        if jid_from_str in self.clients:
            client = self.clients[jid_from_str]
            resource = jid_from.getResource()
            if p_type in ("available", "probe", None):
                if jid_to == TRANSPORT_ID and resource not in client.resources:
                    logger.debug("%s from user %s, will send sendInitPresence" % (p_type, jid_from_str))
                    client.resources.append(resource)
                    if client.lastStatus == "unavailable" and len(client.resources) == 1:
                        if not client.vk.Online:
                            client.vk.Online = True
                    client.send_init_presence()

            elif p_type == "unavailable":
                if jid_to == TRANSPORT_ID and resource in client.resources:
                    client.resources.remove(resource)
                    if client.resources:
                        client.send_out_presence(jid_from)
                if not client.resources:
                    stanza_send(cl, xmpp.Presence(jid_from, "unavailable", frm=TRANSPORT_ID))
                    client.vk.disconnect()
                    if jid_from_str in self.gateway.clients:
                        del self.gateway.clients[jid_from_str]
                    self.gateway.update_transports_list(jid_from_str, False)

            elif p_type == "error":
                eCode = prs.getErrorCode()
                if eCode == "404":
                    client.vk.disconnect()

            elif p_type == "subscribe":
                if jid_to_str == TRANSPORT_ID:
                    stanza_send(cl, xmpp.Presence(jid_from_str, "subscribed", frm=TRANSPORT_ID))
                    stanza_send(cl, xmpp.Presence(jid_from, frm=TRANSPORT_ID))
                else:
                    stanza_send(cl, xmpp.Presence(jid_from_str, "subscribed", frm=jid_to))
                    if client.friends:
                        id = vk2xmpp(jid_to_str)
                        if id in client.friends:
                            if client.friends[id]["online"]:
                                stanza_send(cl, xmpp.Presence(jid_from, frm=jid_to))
            elif p_type == "unsubscribe":
                if jid_from_str in self.clients and jid_to_str == TRANSPORT_ID:
                    client.delete_user(True)
                    watcher_msg(_("User removed registration: %s") % jid_from_str)

            if jid_to_str == TRANSPORT_ID:
                client.lastStatus = p_type

        elif p_type in ("available", None):
            logger.debug("User %s not in transport but want to be in" % jid_from_str)
            with Database(DB_FILE) as db:
                db("select * from users where jid=?", (jid_from_str,))
                user = db.fetchone()
                if user:
                    logger.debug("User %s found in db" % jid_from_str)
                    jid, phone = user[:2]
                    self.clients[jid] = user = TUser(self.gateway, (phone, None), jid)
                    try:
                        if user.connect():
                            user.init(None, True)
                            self.gateway.update_transports_list(user)
                        else:
                            dump_crash("prs.connect", 0, False)
                            msg_send(self.gateway.component, jid, _(
                                "Auth failed! If this error repeated, please register again. This incident will be reported."),
                                    TRANSPORT_ID)
                    except Exception as e:
                        logger.critical('Error while adding user: %s' % e)
                        dump_crash("prs.init")


def get_handler(gateway):
    return PresenceHandler(gateway).handle