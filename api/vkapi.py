from __future__ import unicode_literals
import logging
import requests
import ujson as json

import database
from friends import get_friend_jid
from errors import AuthenticationException, CaptchaNeeded, NotAllowed, AccessRevokedError, InvalidTokenError
from messaging.parsing import escape_name
from parallel import realtime
from parallel.sending import send
from compat import text_type, get_logger
import time

from config import MAX_API_RETRY, API_MAXIMUM_RATE, TRANSPORT_ID
VK_ERROR_BURST = 6
_logger = get_logger()


def method(method_name, jid, args=None, additional_timeout=0, retry=0, token=None):
    """
    Makes post-request to vk api witch burst protection and exception handling
    @type jid: text_type
    @type method_name: text_type
    @param method_name: vk api method name
    @param jid: client jid
    @param args: method parameters
    @param additional_timeout: time in seconds to wait before reattempting
    @return: @raise NotImplementedError:
    """
    assert isinstance(method_name, text_type)
    assert isinstance(jid, text_type)

    if retry > MAX_API_RETRY:
        logging.error('reached max api retry for %s, %s' % (method_name, jid))
        return None

    args = args or {}
    url = 'https://api.vk.com/method/%s' % method_name
    token = token or realtime.get_token(jid)

    if not token:
        raise ValueError('no token for %s' % jid)

    args['access_token'] = token
    args["v"] = '3.0'

    _logger.debug('api method %s, arguments: %s' % (method_name, args))

    if additional_timeout:
        time.sleep(additional_timeout)

    realtime.wait_for_api_call(jid)

    try:
        response = requests.post(url, args)
        if response.status_code != 200:
            _logger.debug('no response')
            raise requests.HTTPError('no response')
    except requests.RequestException as e:
        _logger.debug('method error: %s' % e)

        if not additional_timeout:
            additional_timeout = 1

        additional_timeout *= 2

        return method(method_name, jid, args, additional_timeout, retry)

    text = response.text
    assert not (text is None)
    body = json.loads(text)

    if 'response' in body:
        return body['response']

    if 'error' in body:
        code = body['error']['error_code']

        if code == VK_ERROR_BURST:
            _logger.debug('too many requests per second, trying again')
            if additional_timeout:
                additional_timeout *= 2
            else:
                additional_timeout = API_MAXIMUM_RATE
            return method(method_name, jid, args, additional_timeout, retry + 1)

    raise NotImplementedError('unable to process %s' % body)


def method_wrapped(m, jid, args=None, token=None):
    """

    @type jid: text_type
    @param jid: client jid
    @param m: method name
    @param args: method arguments
    @return: @raise NotImplementedError:
    """
    args = args or {}
    result = {}

    assert isinstance(jid, text_type)
    assert isinstance(m, text_type)
    assert isinstance(args, dict)

    _logger.debug('wrapped %s, args=%s, t=%s' % (m, args, token))

    try:
        result = method(m, jid, args, token=token)
    except CaptchaNeeded:
        _logger.error("VKLogin: running captcha challenge for %s" % jid)
        # TODO: Captcha
        raise NotImplementedError('Captcha')
    except NotAllowed:
        send(jid, "You're not allowed to perform this action.",
             get_friend_jid(args.get("user_id", TRANSPORT_ID)))
    except AccessRevokedError:
        _logger.debug('user %s revoked access' % jid)
        database.remove_user(jid)
        realtime.remove_online_user(jid)
    except InvalidTokenError:
        send(jid, 'Your token is invalid. Please, register again', TRANSPORT_ID)

    return result


def is_application_user(jid, token):
    """
    Check if client is application user and validate token
    @type jid: text_type
    @param jid: client jid
    @return:
    """
    _logger.debug('login api: checking token')

    assert isinstance(jid, text_type)

    try:
        method_wrapped('isAppUser', jid, token=token)
        _logger.debug('token for %s is valid' % jid)
        return True
    except AuthenticationException as auth_e:
        _logger.debug('checking token failed: %s' % auth_e)
        return False


def mark_messages_as_read(jid, msg_list):
    method("messages.markAsRead", jid, {"message_ids": ','.join(msg_list)})


def get_messages(jid, count=5, last_msg_id=None):
    _logger.debug('getting messages for %s' % jid)
    arguments = {"out": 0, "filters": 1, "count": count}
    if last_msg_id:
        arguments.update({'last_message_id': last_msg_id})
    else:
        arguments.update({'count': count})
    return method("messages.get", jid, arguments)


def get_user_data(uid, target_uid, fields=None):
    _logger.debug('user api: sending user data for %s about %s' % (uid, target_uid))
    fields = fields or ["screen_name"]
    args = {"fields": ",".join(fields), "user_ids": target_uid}
    m = "users.get"
    data = method(m, uid, args)

    if data:
        data = data[0]
        data["name"] = escape_name("", u"%s %s" % (data["first_name"], data["last_name"]))
        del data["first_name"], data["last_name"]
    else:
        data = {}
        for key in fields:
            data[key] = "Unknown error when trying to get user data. We're so sorry."
    return data