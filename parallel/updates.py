# coding=utf-8
from __future__ import unicode_literals

from user import UserApi
from friends import get_friend_jid
from cystanza.stanza import Presence
from compat import get_logger


NEW_MESSAGE = 4
FRIEND_ONLINE = 8
FRIEND_OFFLINE = 9
FRIEND_TYPING_CHAT = 61
FRIEND_TYPING_GROUP = 62
_logger = get_logger()


def handle_update(jid, data):
    try:
        code, friend_id = data[0], abs(data[1])
    except (IndexError, ValueError) as e:
        return _logger.error('unable to process update data %s: %s' % (data, e))

    if code == NEW_MESSAGE:
        return UserApi(jid).vk.messages.send_messages()

    origin = get_friend_jid(friend_id)

    if code == FRIEND_ONLINE:
        return Presence(origin, jid)

    if code == FRIEND_OFFLINE:
        return Presence(origin, jid, presence_type='unavailable')

    _logger.debug('doing nothing on code %s' % code)