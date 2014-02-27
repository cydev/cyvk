import traceback

from compat import get_logger
from .errors import ApiError


_logger = get_logger()


class ApiWrapper(object):
    def __init__(self, api):
        self.api = api

    def method(self, *args, **kwargs):
        return self.api.method(*args, **kwargs)

    @property
    def jid(self):
        return self.api.jid


def method_wrapper(f):
    def wrapper(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except (KeyError, ValueError, TypeError, IndexError, ApiError) as e:
            tb = traceback.format_exc(e)
            _logger.error('method error: \n%s' % tb)

    return wrapper
