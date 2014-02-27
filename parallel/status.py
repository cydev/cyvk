from __future__ import unicode_literals
from friends import get_friend_jid
from parallel import realtime
from parallel.stanzas import push
from compat import get_logger
from cystanza.stanza import Presence

_logger = get_logger()


def update_friend_status(jid, friend_uid, status=None, friend_nickname=None, reason=None):
    """
    Send new friend status to client
    @type friend_nickname: unicode
    @type status: unicode
    @type friend_uid: int
    @type jid: unicode
    @param reason: stanza that contains reason of update
    """
    _logger.debug('sending %s status -> %s' % (friend_uid, jid))
    friends = realtime.get_friends(jid)
    friend_is_online = status == 'online'
    friends[friend_uid]['online'] = friend_is_online
    realtime.set_friends(jid, friends)
    origin = get_friend_jid(friend_uid)
    presence_type = None
    if not friend_is_online:
        presence_type = 'unavailable'
    stanza = Presence(origin, jid, reason, nickname=friend_nickname, presence_type=presence_type)
    push(stanza)

