__author__ = 'ernado'


class AuthenticationException(Exception):
    pass

class ConnectionError(Exception):
    pass

class APIError(Exception):
    pass


class CaptchaNeeded(APIError):
    pass


class TokenError(APIError):
    pass


class NotAllowed(APIError):
    pass

class TooManyRequests(APIError):
    pass




all_errors = (AuthenticationException, ConnectionError, APIError)