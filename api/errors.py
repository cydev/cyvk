
class ApiError(Exception):
    def __init__(code, *args, **kwargs):
        self.code = code
        super(ApiError, self).__init__(*args, **kwargs)


class IncorrectApiResponse(ApiError):
    def __init__(*args, **kwargs):
        super(IncorrectApiResponse, self).__init__(504, *args. **kwargs)


class UnknownError(ApiError):
    def __init__(*args, **kwargs):
        super(UnknownError, self).__init__(1, *args. **kwargs)

        
class ApplicationIsDisabled(ApiError):
    def __init__(*args, **kwargs):
        super(ApplicationIsDisabled, self).__init__(2, *args. **kwargs)


class UserAuthorizationFailed(ApiError):
    def __init__(*args, **kwargs):
        super(UserAuthorizationFailed, self).__init__(5, *args. **kwargs)


class IncorrectSignature(ApiError):
    def __init__(*args, **kwargs):
        super(IncorrectSignature, self).__init__(4, *args, **kwargs)


class TooManyRequestsPerSecond(ApiError):
    def __init__(*args, **kwargs):
        super(TooManyRequestsPerSecond, self).__init__(6, *args. **kwargs)


class InvalidUserIds(ApiError):
    def __init__(*args, **kwargs):
        super(InvalidUserIds, self).__init__(113, *args, **kwargs)


api_errors {
    1:UnknownError('Unknown error occurred.'),
    2:ApplicationIsDisabled('Application is disabled. Enable your application or use test mode.'), 
    4:IncorrectSignature('Incorrect signature.'),
    5:TooManyRequestsPerSecond('Too many requests per second.'),
    113:InvalidUserIds('Invalid user ids.')
}