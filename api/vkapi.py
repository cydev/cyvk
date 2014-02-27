from __future__ import unicode_literals
import time
import ujson as json

import requests

from .errors import (api_errors, UnknownError, IncorrectApiResponse, TooManyRequestsPerSecond, AuthenticationException,
                     InvalidTokenError)
# from errors import AuthenticationException, CaptchaNeeded, NotAllowed, AccessRevokedError
from parallel import realtime
from compat import text_type, get_logger
from config import MAX_API_RETRY, API_MAXIMUM_RATE, TRANSPORT_ID
from .user import UserApi
from .messages import MessagesApi
from parallel.realtime import get_token
from parallel.sending import push
from cystanza.stanza import ChatMessage
from .api import method_wrapper

VK_ERROR_BURST = 6
WAIT_RATE = 2.
_logger = get_logger()


class Api(object):
    URL = 'https://api.vk.com/method/%s'
    VERSION = '3.0'

    def __init__(self, jid, token=None):
        if not isinstance(jid, text_type):
            raise ValueError('Expected %s jid, got %s' % (text_type, type(jid)))
        self.jid = jid
        token = token or get_token(jid)
        if not token:
            # TODO: send error to user
            raise ValueError('No token for %s' % jid)
        self.token = token
        self.user = UserApi(self)
        self.messages = MessagesApi(self)

    def _method(self, method_name, args=None, additional_timeout=0, retry=0):
        """
        Makes post-request to vk api witch burst protection and exception handling
        @type method_name: text_type
        @param method_name: vk api method name
        @param args: method parameters
        @param additional_timeout: time in seconds to wait before reattempting
        """
        assert isinstance(method_name, text_type)

        if retry > MAX_API_RETRY:
            raise IncorrectApiResponse('reached max api retry for %s, %s' % (method_name, self.jid))

        args = args or {}
        args.update({'v': self.VERSION, 'access_token': self.token})
        _logger.debug('calling api method %s, arguments: %s' % (method_name, args))

        time.sleep(additional_timeout)
        realtime.wait_for_api_call(self.jid)

        try:
            response = requests.post(self.URL % method_name, args)
            if response.status_code != 200:
                raise requests.HTTPError('incorrect response status code')
            body = json.loads(response.text)
            _logger.debug('got: %s' % body)
            if 'response' in body:
                return body['response']
            if 'error' in body and 'error_code' in body['error']:
                code = body['error']['error_code']
                raise api_errors.get(code, UnknownError())
            raise NotImplementedError('unable to process %s' % body)
        except (requests.RequestException, ValueError) as e:
            _logger.error('method error: %s' % e)
            additional_timeout = additional_timeout or 1
        except TooManyRequestsPerSecond:
            additional_timeout = additional_timeout or API_MAXIMUM_RATE / WAIT_RATE
        additional_timeout *= WAIT_RATE
        return self._method(method_name, args, additional_timeout, retry + 1)

    @method_wrapper
    def method(self, method_name, args=None, raise_auth=False):
        """Call method with error handling"""
        try:
            return self._method(method_name, args)
        # except CaptchaNeeded:
        #     _logger.error('captcha challenge for %s' % self.jid)
        #     raise NotImplementedError('captcha')
        except AuthenticationException as e:
            push(ChatMessage(TRANSPORT_ID, self.jid, 'Authentication error: %s' % e))
        # except NotAllowed:
        #     friend_jid = get_friend_jid(args.get('user_id', TRANSPORT_ID))
        #     text = "You're not allowed to perform this action"
        #     push(ChatMessage(friend_jid, self.jid, text))
        # except AccessRevokedError:
        #     _logger.debug('user %s revoked access' % self.jid)
        #     push(ChatMessage(TRANSPORT_ID, self.jid, "You've revoked access and will be unregistered from transport"))
        #     database.remove_user(self.jid)
        #     realtime.remove_online_user(self.jid)
        except InvalidTokenError:
            push(ChatMessage(TRANSPORT_ID, self.jid, 'Your token is invalid. Please, register again'))
        except NotImplementedError as e:
            push(ChatMessage(TRANSPORT_ID, self.jid, 'Feature not implemented: %s' % e))

        if raise_auth:
            raise AuthenticationException()

    @method_wrapper
    def is_application_user(self):
        """Check if client is application user and validate token"""
        try:
            self.method('isAppUser', raise_auth=True)
            return True
        except AuthenticationException:
            return False
