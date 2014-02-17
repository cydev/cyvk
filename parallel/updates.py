# coding=utf-8
from __future__ import unicode_literals
import time
from api.vkapi import get_messages, mark_messages_as_read, method
from friends import get_friend_jid
import messaging.message
from messaging.parsing import sorting, escape, escape_name
from parallel import status, realtime, sending
from parallel.sending import send_typing_status
from compatibility import HTMLParser

from config import USE_LAST_MESSAGE_ID

__author__ = 'ernado'

#
# 0,$message_id,0 -- удаление сообщения с указанным local_id
# 1,$message_id,$flags -- замена флагов сообщения (FLAGS:=$flags)
# 2,$message_id,$mask[,$user_id] -- установка флагов сообщения (FLAGS|=$mask)
# 3,$message_id,$mask[,$user_id] -- сброс флагов сообщения (FLAGS&=~$mask)
# 4,$message_id,$flags,$from_id,$timestamp,$subject,$text,$attachments -- добавление нового сообщения
# 8,-$user_id,0 -- друг $user_id стал онлайн
# 9,-$user_id,$flags -- друг $user_id стал оффлайн ($flags равен 0, если пользователь покинул сайт (например, нажал выход) и 1, если оффлайн по таймауту (например, статус away))
#
# 51,$chat_id,$self -- один из параметров (состав, тема) беседы $chat_id были изменены. $self - были ли изменения вызываны самим пользователем
# 61,$user_id,$flags -- пользователь $user_id начал набирать текст в диалоге. событие должно приходить раз в ~5 секунд при постоянном наборе текста. $flags = 1
# 62,$user_id,$chat_id -- пользователь $user_id начал набирать текст в беседе $chat_id.
# 70,$user_id,$call_id -- пользователь $user_id совершил звонок имеющий идентификатор $call_id, дополнительную информацию о звонке можно получить используя метод voip.getCallInfo.


NEW_MESSAGE = 4
FRIEND_ONLINE = 8
FRIEND_OFFLINE = 9
FRIEND_TYPING_CHAT = 61
FRIEND_TYPING_GROUP = 62

import logging

logger = logging.getLogger("cyvk")

import friends


def process_data(jid, data):
    code = data[0]

    if code == FRIEND_ONLINE:
        friend_id = data[1]
        if friend_id < 0:
            friend_id = -friend_id
        status.update_friend_status(jid, friend_id, status='online')
        return

    if code == FRIEND_OFFLINE:
        friend_id = data[1]
        if friend_id < 0:
            friend_id = -friend_id
        status.update_friend_status(jid, friend_id, status='unavailable')
        return

    if code == NEW_MESSAGE:
        return send_messages(jid)

    if code == FRIEND_TYPING_CHAT:
        friend_id = data[1]
        if friend_id < 0:
            friend_id = -friend_id
        return send_typing_status(jid, friends.get_friend_jid(friend_id))

    logger.debug('doing nothing on code %s' % code)


def send_messages(jid):
    logger.debug('user api: send_messages for %s' % jid)

    if not jid:
        raise ValueError('user api: unable to send messages for blank jid')

    last_message = realtime.get_last_message(jid)

    messages = get_messages(jid, 200, last_message)

    if not messages:
        return

    messages = sorted(messages[1:], sorting)

    if not messages:
        return

    read = []

    last_message = messages[-1]["mid"]

    if USE_LAST_MESSAGE_ID:
        realtime.set_last_message(jid, last_message)

    for message in messages:
        read.append(str(message["mid"]))
        from_jid = get_friend_jid(message["uid"])
        webtools = HTMLParser()
        body = webtools.unescape(message["body"]).replace('<br>', '\n')
        body += messaging.message.parse(jid, message)
        sending.send(jid, escape("", body), from_jid, message["date"])

    mark_messages_as_read(jid, read)


def send_message(jid, body, destination_uid):
    logger.debug('user api: message to %s' % destination_uid)

    assert isinstance(jid, unicode)
    assert isinstance(destination_uid, unicode)
    assert isinstance(body, unicode)

    method_name = "messages.send"
    method_values = {'user_id': int(destination_uid), "message": body, "type": 0}
    update_last_activity(jid)

    return method(method_name, jid, method_values)


def update_last_activity(uid):
    logger.debug('updating last activity')
    realtime.set_last_activity(uid, time.time())


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