from __future__ import unicode_literals
import logging
import time

import ujson as json
import requests

import database
from friends import get_friend_jid
from errors import AuthenticationException, CaptchaNeeded, NotAllowed, AccessRevokedError, InvalidTokenError
from parallel import realtime
from parallel.sending import send
from compat import text_type, get_logger
from config import MAX_API_RETRY, API_MAXIMUM_RATE, TRANSPORT_ID
from api.user import UserApi
from api.messages import MessagesApi


VK_ERROR_BURST = 6
_logger = get_logger()


class IncorrectApiResponce(exception):
	pass
		

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
		self.user = UserApi(self, jid)
		self.messages = MessagesApi(self, jid)

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
	        raise TooMuchAttemts('reached max api retry for %s, %s' % (method_name, jid))

	    args = args or {}
	    args.update({'v' self.VERSION, 'access_token': self.token})
	    _logger.debug('calling api method %s, arguments: %s' % (method_name, args))

	    time.sleep(additional_timeout)
	    realtime.wait_for_api_call(jid)

	    try:
	        response = requests.post(self.URL % method_name, args)
	        if response.status_code != 200:
	            raise requests.HTTPError('no response')
	        body = json.loads(response.text)
		    if 'response' in body:
		        return body['response']	
		    code = None
		   	if 'error' in body and 'error_code' in body['error']:
	        	code = body['error']['error_code']
	        if code == VK_ERROR_BURST:
	        	additional_timeout = additional_timeout or API_MAXIMUM_RATE
	        	raise IncorrectApiResponce(code)
	        raise NotImplementedError('unable to process %s' % body)
		                
	    except (requests.RequestException, IncorrectApiResponce) as e:
	        _logger.error('method error: %s' % e)

	        if not additional_timeout:
	            additional_timeout = 1
	        additional_timeout *= 2

	        return self._method(method_name, args, additional_timeout, retry+1)   

	def method(self, method_name, args=None, additional_timeout=0, retry=0):
	    """Call method with error handling"""
	    try:
	        return self._method(method_name, args=None, additional_timeout=0, retry=0)
	    except CaptchaNeeded:
	        _logger.error('captcha challenge for %s' % jid)
	        raise NotImplementedError('captcha')
	    except AuthenticationException as e:
	    	send(jid, 'Authentication error: %s' % e)
	    except NotAllowed:
	    	friend_jid = get_friend_jid(args.get('user_id', TRANSPORT_ID))
	    	text = "You're not allowed to perform this action"
	        send(self.jid, text, friend_jid)
	    except AccessRevokedError:
	        _logger.debug('user %s revoked access' % self.jid)
	        database.remove_user(self.jid)
	        realtime.remove_online_user(self.jid)
	    except InvalidTokenError:
	        send(self.jid, 'Your token is invalid. Please, register again', TRANSPORT_ID)
	    except IncorrectApiResponce:
	    	send(self.jid, 'Unable to retrieve correct response from vk api')
	    except NotImplementedError as e:
	    	send(self.jid, 'Feature not implemented: %s' % e)
	    
	    if reraise_auth:
	    	raise AuthenticationException()

		def is_application_user(self):
		    """Check if client is application user and validate token"""
		    try:
		        self.method('isAppUser', reraise_auth=True)
		        return True
		    except AuthenticationException:
		        return False