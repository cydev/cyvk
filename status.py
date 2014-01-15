__author__ = 'ernado'

import logging

from library.xmpp.protocol import Presence, NS_NICK
from friends import get_friend_jid
import database


logger = logging.getLogger("vk4xmpp")

def send_friend_status(jid, friend_uid, presence_type=None, nick=None, reason=None):
    logger.debug('sending %s status -> %s' % (friend_uid, jid))
    friends = database.get_friends(jid)
    friends[friend_uid]['online'] = presence_type is None
    database.set_friends(jid, friends)
    presence = Presence(jid, presence_type, frm=get_friend_jid(friend_uid), status=reason)
    if nick:
        presence.setTag("nick", namespace=NS_NICK)
        presence.setTagData("nick", nick)
    database.queue_stanza(presence)
