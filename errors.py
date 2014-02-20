__author__ = 'ernado'


class AuthenticationException(Exception):
    pass


class ConnectionError(Exception):
    pass


class APIError(Exception):
    def __init__(self, message):
        self.message = message


class CaptchaNeeded(APIError):
    pass


class InvalidTokenError(APIError):
    pass


class AccessRevokedError(APIError):
    pass


class NotAllowed(APIError):
    pass


class TooManyRequests(APIError):
    pass


all_errors = (AuthenticationException, ConnectionError, APIError)