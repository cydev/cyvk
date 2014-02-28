from __future__ import unicode_literals
import time

from .api import ApiWrapper, method_wrapper
from .parsing import sorting, escape, MessageParser
from friends import get_friend_jid
from compat import html_unespace
from cystanza.stanza import ChatMessage


class Message(object):
    def __init__(self, origin, text, date):
        self.origin = origin
        self.text = text
        self.date = date


class MessagesApi(ApiWrapper):
    def __init__(self, api):
        self._parser = MessageParser(api)
        self.last_id = None
        super(MessagesApi, self).__init__(api)

    @method_wrapper
    def parse(self, message):
        return self._parser.parse(message)

    @method_wrapper
    def mark_as_read(self, message_list):
        self.method('messages.markAsRead', dict(message_ids=','.join(message_list)))

    @method_wrapper
    def get(self, count=5):
        assert isinstance(count, int)

        if count > 100:
            count = 100
        arguments = dict(out=0, filters=1, count=count)
        if self.last_id:
            arguments.update({'last_message_id': self.last_id})
        messages = sorted(self.method('messages.get', arguments)[1:], sorting)
        if not messages:
            return
        read = []
        messages_return = []
        self.last_id = messages[-1]["mid"]

        for message in messages:
            read.append(str(message["mid"]))
            from_jid = get_friend_jid(message["uid"])
            body = html_unespace(message['body'])
            body += self.parse(message)
            text = escape("", body)
            messages_return.append(Message(from_jid, text, message["date"]))

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

    @method_wrapper
    def send_messages(self):
        messages = self.get(200) or []

        if messages is None:
            return

        for message in messages:
            timestamp = time.strftime("%Y%m%dT%H:%M:%S", time.gmtime(message.date))
            send = self.api.user.transport.send
            send(ChatMessage(message.origin, self.jid, message.text, timestamp=timestamp))

            # @method_wrapper
            # def send_messages(self):
            # messages = get(200) or []
            # for message in messages:
            #     timestamp = time.strftime("%Y%m%dT%H:%M:%S", time.gmtime(message.date))
            #     push(ChatMessage(message.origin, jid, message.text, timestamp=timestamp))