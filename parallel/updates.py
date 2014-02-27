# coding=utf-8
from __future__ import unicode_literals
import time

from api.vkapi import Api
from parallel.stanzas import push
from friends import get_friend_jid
from cystanza.stanza import ChatMessage, Presence
from compat import get_logger


NEW_MESSAGE = 4
FRIEND_ONLINE = 8
FRIEND_OFFLINE = 9
FRIEND_TYPING_CHAT = 61
FRIEND_TYPING_GROUP = 62
_logger = get_logger()


def process_data(jid, data):
    try:
        code, friend_id = data[0], abs(data[1])
    except (IndexError, ValueError) as e:
        return _logger.error('unable to process update data %s: %s' % (data, e))

    if code == NEW_MESSAGE:
        return send_messages(jid)

    origin = get_friend_jid(friend_id)

    if code == FRIEND_ONLINE:
        return Presence(origin, jid)

    if code == FRIEND_OFFLINE:
        return Presence(origin, jid, presence_type='unavailable')

    _logger.debug('doing nothing on code %s' % code)


def send_messages(jid):
    api = Api(jid)
    messages = api.messages.get(200) or []
    for message in messages:
        timestamp = time.strftime("%Y%m%dT%H:%M:%S", time.gmtime(message.date))
        push(ChatMessage(message.origin, jid, message.text, timestamp=timestamp))


def send_message(jid, body, destination_uid):
    _logger.debug('user api: message to %s' % destination_uid)
    api = Api(jid)
    return api.messages.send_message(body, destination_uid)


def set_online(user):
    api = Api(user)
    return api.user.set_online()


def get_friends(jid, fields=None):
    api = Api(jid)
    return api.user.get_friends(fields)
