from __future__ import unicode_literals

import logging

from xmpp.protocol import Presence, NS_NICK, Protocol
from friends import get_friend_jid
import realtime

logger = logging.getLogger("vk4xmpp")


def update_friend_status(jid, friend_uid, status=None, friend_nickname=None, reason=None):
    """
    Send new friend status to client
    @type reason: Protocol
    @type friend_nickname: unicode
    @type status: unicode
    @type friend_uid: int
    @type jid: unicode
    @param reason: stanza that contains reason of update
    """
    logger.debug('sending %s status -> %s' % (friend_uid, jid))

    # Todo: implement storage for friend statuses

    # updating friend list
    # it must be atomic in ideal implementation
    friends = realtime.get_friends(jid)
    friends[friend_uid]['online'] = status is None
    realtime.set_friends(jid, friends)

    # generating stanza
    presence = Presence(jid, status, frm=get_friend_jid(friend_uid), status=reason)

    if friend_nickname:
        presence.setTag('nick', namespace=NS_NICK)
        presence.setTagData('nick', friend_nickname)

    # adding stanza to queue
    realtime.queue_stanza(presence)
