from parallel.sending import push
from cystanza.stanza import ChatMessage
from config import TRANSPORT_ID
from compat import get_logger
import traceback

_logger = get_logger()


class ApiWrapper(object):
    def __init__(self, api, jid):
        self.jid = jid
        self.api = api

    def method(self, *args, **kwargs):
        return self.api.method(*args, **kwargs)


def method_wrapper(f):
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except (KeyError, ValueError, TypeError, IndexError) as e:
            tb = traceback.format_exc(e)
            _logger.error('method error: \n%s' % tb)
            push(ChatMessage(TRANSPORT_ID, self.jid, 'Unable to process vk api responce'))

    return wrapper
