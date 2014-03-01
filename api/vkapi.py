from __future__ import unicode_literals
import time

from compat import text_type, get_logger, requests, json
from config import MAX_API_RETRY, API_MAXIMUM_RATE, TRANSPORT_ID
from .errors import (api_errors, UnknownError, IncorrectApiResponse, TooManyRequestsPerSecond, AuthenticationException,
                     InvalidTokenError)
from .messages import MessagesApi
from .api import method_wrapper
from .parsing import escape_name
from .polling import LongPolling
from cystanza.stanza import ChatMessage


VK_ERROR_BURST = 6
WAIT_RATE = 2.
_logger = get_logger()


class Api(object):
    URL = 'https://api.vk.com/method/%s'
    VERSION = '3.0'

    def __init__(self, user, ):
        self.user = user
        self.jid = user.jid
        self.messages = MessagesApi(self)
        self.last_method_time = 0
        self.polling = LongPolling(self)

    @property
    def token(self):
        return self.user.token

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
        now = time.time()
        diff = now - self.last_method_time
        if diff < API_MAXIMUM_RATE:
            _logger.debug('burst protected')
            time.sleep(abs(diff - API_MAXIMUM_RATE))
        self.last_method_time = now

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
            self.user.transport.send(ChatMessage(TRANSPORT_ID, self.jid, 'Authentication error: %s' % e))
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
            self.user.transport.send((ChatMessage(TRANSPORT_ID, self.jid, 'Your token is invalid. Register again')))
        except NotImplementedError as e:
            self.user.transport.send((ChatMessage(TRANSPORT_ID, self.jid, 'Feature not implemented: %s' % e)))

        if raise_auth:
            raise AuthenticationException()

    @method_wrapper
    def get(self, uid, fields=None):
        fields = fields or ['screen_name']
        args = dict(fields=','.join(fields), user_ids=uid)
        data = self.method('users.get', args)[0]
        data['name'] = escape_name('', u'%s %s' % (data['first_name'], data['last_name']))
        del data['first_name'], data['last_name']
        return data

    @method_wrapper
    def set_online(self):
        self.method("account.setOnline")

    @method_wrapper
    def get_friends(self, fields=None, online=None):
        fields = fields or ["screen_name"]
        method_name = "friends.get"
        if online:
            method_name = "friends.getOnline"
        friends_raw = self.method(method_name, {"fields": ",".join(fields)}) or {}
        friends = {}
        for friend in friends_raw:
            uid = friend["uid"]
            name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
            friends[uid] = {"name": name, "online": friend["online"]}
            for key in fields:
                if key != "screen_name":
                    friends[uid][key] = friend.get(key)
        return friends

    @method_wrapper
    def is_application_user(self):
        """Check if client is application user and validate token"""
        try:
            self.method('isAppUser', raise_auth=True)
            return True
        except AuthenticationException:
            return False
