from __future__ import unicode_literals

import logging
from friends import get_friend_jid
from parallel import realtime
from parallel.stanzas import push
from transport.statuses import get_status_stanza

logger = logging.getLogger("cyvk")


def update_friend_status(jid, friend_uid, status=None, friend_nickname=None, reason=None):
    """
    Send new friend status to client
    @type friend_nickname: unicode
    @type status: unicode
    @type friend_uid: int
    @type jid: unicode
    @param reason: stanza that contains reason of update
    """
    logger.debug('sending %s status -> %s' % (friend_uid, jid))

    friends = realtime.get_friends(jid)
    friends[friend_uid]['online'] = status == 'online'
    realtime.set_friends(jid, friends)

    status_stanza = get_status_stanza(jid, get_friend_jid(friend_uid), friend_nickname, status, reason)

    push(status_stanza)

