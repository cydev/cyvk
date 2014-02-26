# coding=utf-8
from __future__ import unicode_literals
from api.test_api import Api
from parallel import status, sending
from cystanza.stanza import ChatMessage
from compat import get_logger
import time

NEW_MESSAGE = 4
FRIEND_ONLINE = 8
FRIEND_OFFLINE = 9
FRIEND_TYPING_CHAT = 61
FRIEND_TYPING_GROUP = 62
_logger = get_logger()


def process_data(jid, data):
    code = data[0]

    if code == NEW_MESSAGE:
        return send_messages(jid)

    friend_id = abs(data[1])

    if code == FRIEND_ONLINE:
        return status.update_friend_status(jid, friend_id, status='online')

    if code == FRIEND_OFFLINE:
        return status.update_friend_status(jid, friend_id, status='unavailable')

    # if code == FRIEND_TYPING_CHAT:
    #     return send_typing_status(jid, friends.get_friend_jid(friend_id))

    _logger.debug('doing nothing on code %s' % code)


def send_messages(jid):
    api = Api(jid)
    messages = api.messages.get(200) or []
    for message in messages:
        timestamp = time.strftime("%Y%m%dT%H:%M:%S", time.gmtime(message.date))
        sending.push(ChatMessage(message.origin, jid, message.text, timestamp=timestamp))
        sending.send(jid, message.origin, message.text, message.date)


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
