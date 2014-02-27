from api.test_api import Api
from cystanza.stanza import ChatMessage
from parallel.sending import push


class UserApi(object):
    def __init__(self, jid):
        self.jid = jid
        self._vk = None
        self._friends = None

    @property
    def vk(self):
        # lazy loading
        if not self._vk:
            api = Api(self.jid)
            self._vk = api
        return self._vk

    @staticmethod
    def send(stanza):
        push(stanza)

    def send_message(self, origin, text):
        self.send(ChatMessage(origin, self.jid, text))

    @property
    def friends(self):
        return None

    def set_online(self):
        pass

    def set_offline(self):
        pass

    def remove(self):
        pass

    def subscribe(self, subscribtions=None):
        pass

    def load(self):
        pass
