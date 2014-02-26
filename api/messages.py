from __future__ import unicode_literals
from .api import ApiWrapper, method_wrapper
from parallel import realtime
from .parsing import sorting, escape
from .message import parse
from friends import get_friend_jid
from compat import html_unespace


class Message(object):
    def __init__(self, origin, text, date):
        self.origin = origin
        self.text = text
        self.date = date


class MessagesApi(ApiWrapper):
    @method_wrapper
    def mark_as_read(self, message_list):
        self.method('messages.markAsRead', self.jid, dict(message_ids=','.join(message_list)))

    @method_wrapper
    def get(self, count=5):
        assert isinstance(count, int)

        if count > 100:
            count = 100
        jid = self.jid
        last_message_id = realtime.get_last_message(jid)
        arguments = dict(out=0, filters=1, count=count)
        if last_message_id:
            arguments.update({'last_message_id': last_message_id})
        messages = sorted(self.method('messages.get', arguments)[1:], sorting)
        read = []
        messages_return = []
        if not messages:
            return
        last_message_id = messages[-1]["mid"]
        realtime.set_last_message(jid, last_message_id)

        for message in messages:
            read.append(str(message["mid"]))
            from_jid = get_friend_jid(message["uid"])
            body = html_unespace(message['body'])
            body += parse(jid, message)
            text = escape("", body)
            messages_return.append(Message(text, from_jid, message["date"]))

        self.mark_as_read(read)
        return messages_return

    @method_wrapper
    def get_lp_server(self):
        return self.method('messages.getLongPollServer')

    @method_wrapper
    def send_message(self, body, uid):
        assert isinstance(uid, int)
        assert isinstance(body, unicode)

        return self.method('messages.send', {'user_id': uid, "message": body, "type": 0})
