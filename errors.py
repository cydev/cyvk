__author__ = 'ernado'


class AuthenticationException(Exception):
    pass

class ConnectionError(Exception):
    pass

class VkApiError(Exception):
    pass


class CaptchaNeeded(VkApiError):
    pass


class TokenError(VkApiError):
    pass


class NotAllowed(VkApiError):
    pass


all_errors = (AuthenticationException, ConnectionError)