# coding=utf-8
import messaging

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

import status
import logging
import user as user_api

logger = logging.getLogger("vk4xmpp")

import friends

def process_data(jid, data):
    code = data[0]

    if code == FRIEND_ONLINE:
        friend_id = data[1]
        if friend_id < 0:
            friend_id = -friend_id
        status.update_friend_status(jid, friend_id, status=None)
        return

    if code == FRIEND_OFFLINE:
        friend_id = data[1]
        if friend_id < 0:
            friend_id = -friend_id
        status.update_friend_status(jid, friend_id, status='unavailable')
        return

    if code == NEW_MESSAGE:
        user_api.send_messages(jid)
        # 4,$message_id,$flags,$from_id,$timestamp,$subject,$text,$attachments
        # logger.debug('trying to process message: %s' % data)
        code, message_id, flags, from_id, timestamp, subject, text, attachments = data
        # database.set_last_message(jid, message_id)
        #
        # body = webtools.unescape(text)
        # body += parsers.message.parse_message(jid, text)
        # messaging.send_message(jid, messaging.escape_message("", body), from_id, timestamp)
        return

    if code == FRIEND_TYPING_CHAT:
        friend_id = data[1]
        if friend_id < 0:
            friend_id = -friend_id
        messaging.send_typing_status(jid, friends.get_friend_jid(friend_id))
        return

    logger.debug('doing nothing on code %s' % code)

