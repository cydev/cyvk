# coding=utf-8
from __future__ import unicode_literals
from api.vkapi import get_messages, mark_messages_as_read, method
from friends import get_friend_jid
import friends
import messaging.message
from messaging.parsing import sorting, escape, escape_name
from parallel import status, realtime, sending
from parallel.sending import send_typing_status
from compatibility import HTMLParser
import logging

NEW_MESSAGE = 4
FRIEND_ONLINE = 8
FRIEND_OFFLINE = 9
FRIEND_TYPING_CHAT = 61
FRIEND_TYPING_GROUP = 62
logger = logging.getLogger("cyvk")


def process_data(jid, data):
    code = data[0]

    if code == NEW_MESSAGE:
        return send_messages(jid)

    friend_id = abs(data[1])

    if code == FRIEND_ONLINE:
        return status.update_friend_status(jid, friend_id, status='online')

    if code == FRIEND_OFFLINE:
        return status.update_friend_status(jid, friend_id, status='unavailable')

    if code == FRIEND_TYPING_CHAT:
        return send_typing_status(jid, friends.get_friend_jid(friend_id))

    logger.debug('doing nothing on code %s' % code)


def send_messages(jid):
    logger.debug('user api: send_messages for %s' % jid)

    if not jid:
        raise ValueError('user api: unable to send messages for blank jid')

    last_message_id = realtime.get_last_message(jid)
    messages = get_messages(jid, 200, last_message_id)

    if not messages:
        return

    messages = sorted(messages[1:], sorting)

    if not messages:
        return

    read = []
    last_message_id = messages[-1]["mid"]
    realtime.set_last_message(jid, last_message_id)

    for message in messages:
        read.append(str(message["mid"]))
        from_jid = get_friend_jid(message["uid"])
        parser = HTMLParser()
        body = parser.unescape(message["body"]).replace('<br>', '\n')
        body += messaging.message.parse(jid, message)
        sending.send(jid, escape("", body), from_jid, message["date"])

    mark_messages_as_read(jid, read)


def send_message(jid, body, destination_uid):
    logger.debug('user api: message to %s' % destination_uid)

    assert isinstance(jid, unicode)
    assert isinstance(destination_uid, int)
    assert isinstance(body, unicode)

    method_name = "messages.send"
    method_values = {'user_id': destination_uid, "message": body, "type": 0}
    update_last_activity(jid)

    return method(method_name, jid, method_values)


def update_last_activity(uid):
    logger.debug('updating last activity')
    realtime.set_last_activity_now(uid)


def set_online(user):
    m = "account.setOnline"
    method(m, user)


def get_friends(jid, fields=None):
    logger.debug('getting friends from api for %s' % jid)
    fields = fields or ["screen_name"]
    friends_raw = method("friends.get", jid, {"fields": ",".join(fields)}) or {} # friends.getOnline
    friends = {}
    for friend in friends_raw:
        uid = friend["uid"]
        name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
        try:
            friends[uid] = {"name": name, "online": friend["online"]}
            for key in fields:
                if key != "screen_name":
                    friends[uid][key] = friend.get(key)
        except KeyError as key_error:
            logger.debug('%s while processing %s' % (key_error, uid))
            continue
    return friends