from __future__ import unicode_literals
import logging
import json
import urllib2

import database
from friends import get_friend_jid
import messaging
import webtools
from request_processor import RequestProcessor
import realtime
from errors import AuthenticationException, CaptchaNeeded, NotAllowed, APIError

logger = logging.getLogger("vk4xmpp")

from config import APP_ID, APP_SCOPE, API_MAXIMUM_RATE, TRANSPORT_ID


VK_ERROR_BURST = 6


def method(method_name, jid, args=None, additional_timeout=0):
    """
    Makes post-request to vk api witch burst protection and exception handling
    @type jid: unicode
    @type method_name: unicode
    @param method_name: vk api method name
    @param jid: client jid
    @param args: method parameters
    @param additional_timeout: time in seconds to wait before reattempting
    @return: @raise NotImplementedError:
    """
    logger.debug('api method %s' % method_name)

    assert isinstance(method_name, unicode)
    assert isinstance(jid, unicode)

    # TODO: raise exceptions

    args = args or {}
    url = "https://api.vk.com/method/%s" % method_name
    token =  realtime.get_token(jid)
    # logger.debug('api with token %s' % token)
    args["access_token"] = token
    args["v"] = "3.0"

    realtime.wait_for_api_call(jid)

    rp = RequestProcessor()


    try:
        response = rp.post(url, args)
    except urllib2.URLError as e:
        logger.debug('method error: %s' % e)
        method(method_name, jid, args, additional_timeout=3)
        return

    if not response:
        logger.debug('no response')
        return

    body, response = response

    if not body:
        raise RuntimeError('got blank body')

    body = json.loads(body)

    if "response" in body:
        return body["response"]

    if 'error' in body:
        code = body['error']['error_code']

        if code == VK_ERROR_BURST:
            logger.debug('too many requests per second, trying again')
            if additional_timeout:
                additional_timeout *= 2
            else:
                additional_timeout = API_MAXIMUM_RATE
            return method(method_name, jid, args, additional_timeout=additional_timeout)


    raise NotImplementedError('unsecure method: %s' %  body)


class APIBinding:
    def __init__(self, token, password=None, app_id=APP_ID, scope=APP_SCOPE):
        assert token is not None
        logger.debug('api bindings initialized with token %s' % token)
        self.password = password
        # self.number = number

        self.sid = None
        self.token = token
        self.captcha = {}
        self.last = []
        self.last_method = None

        self.app_id = app_id
        self.scope = scope

        self.rp = RequestProcessor()
        self.attempts = 0

    def login(self):

        raise NotImplementedError('login with password')

        # logger.debug('VKAPI login')
        #
        # url = "https://login.vk.com/"
        # values = {"act": "login",
        #           "utf8": "1", # check if it needed
        #           "email": self.number,
        #           "pass": self.password
        # }
        #
        # body, response = self.rp.post(url, values)
        # remix_sid = self.rp.get_cookie("remixsid")
        #
        # if remix_sid:
        #     self.sid = remix_sid
        #
        # elif "sid=" in response.url:
        #     raise AuthenticationException("Captcha!")
        # else:
        #     raise AuthenticationException("Invalid password")
        #
        # if "security_check" in response.url:
        #     raise AuthenticationException('Security check')
        #     # # TODO: Rewrite
            # # This code should be rewritten! Users from another countries can have problems because of it!
            # security_hash = webtools.regexp(r"security_check.*?hash: '(.*?)'\};", body)[0]
            # code = self.number[2:-2]
            # if len(self.number) == 12:
            #     if not self.number.startswith("+"):
            #         code = self.number[3:-2]        # may be +375123456789
            #
            # elif len(self.number) == 13:            # so we need 1234567
            #     if self.number.startswith("+"):
            #         code = self.number[4:-2]
            #
            # values = {"act": "security_check",
            #           "al": "1",
            #           "al_page": "3",
            #           "code": code,
            #           "hash": security_hash,
            #           "to": ""
            # }
            # post = self.rp.post("https://vk.com/login.php", values)
            # body, response = post
            # if response and not body.split("<!>")[4] == "4":
            #     raise AuthenticationException("Incorrect number")

    def check_sid(self):
        logger.debug('VKAPI check_sid')

        if self.sid:
            url = "https://vk.com/feed2.php"
            get = self.rp.get(url)
            body, response = get
            if body and response:
                data = json.loads(body)
                if data["user"]["id"] != -1:
                    return data

    def confirm(self):
        logger.debug('confirming application')

        url = "https://oauth.vk.com/authorize"
        values = {"display": "mobile",
                  "scope": self.scope,
                  "client_id": self.app_id,
                  "response_type": "token",
                  "redirect_uri": "https://oauth.vk.com/blank.html"
        }

        self.token = None

        body, response = self.rp.get(url, values)

        if not response:
            return

        if "access_token" in response.url:
            self.token = response.url.split("=")[1].split("&")[0]
        else:
            target = webtools.getTagArg("form method=\"post\"", "action", body, "form")
            if target:
                body, response = self.rp.post(target)
                self.token = response.url.split("=")[1].split("&")[0]
            else:
                raise AuthenticationException("Couldn't execute confirmThisApp()!")


    # def unsecure_method(self, method, token, values=None):
    #     logger.debug('VKAPI method %s' % method)
    #     values = values or {}
    #     url = "https://api.vk.com/method/%s" % method
    #     values["access_token"] = token
    #     values["v"] = "3.0"
    #
    #     # TODO: Burst protection
    #     rp = RequestProcessor()
    #
    #     response = rp.post(url, values)
    #
    #     if not response:
    #         logger.debug('no response')
    #         return
    #
    #     body, response = response
    #
    #     if body:
    #         body = json.loads(body)
    #
    #     if "response" in body:
    #         return body["response"]
    #
    #     raise NotImplementedError

    # def method(self, method, values=None):
    #     logger.debug('VKAPI method %s' % method)
    #     values = values or {}
    #     url = "https://api.vk.com/method/%s" % method
    #     values["access_token"] = self.token
    #     values["v"] = "3.0"
    #
    #     # captcha processing
    #     if self.captcha and self.captcha.has_key("key"):
    #         values["captcha_sid"] = self.captcha["sid"]
    #         values["captcha_key"] = self.captcha["key"]
    #         self.captcha = {}
    #
    #     # burst protection
    #     self.last_method = (method, values)
    #     self.last.append(time.time())
    #
    #     if len(self.last) > 2:
    #         if (self.last.pop() - self.last.pop(0)) < 1.1:
    #             time.sleep(0.3)    # warn: it was 0.4 // does it matter?
    #
    #     # post
    #     response = self.rp.post(url, values)
    #
    #     if not response:
    #         logger.debug('no response')
    #         return
    #
    #     body, response = response
    #     if body:
    #         body = json.loads(body)
    #         # Debug:
    #     #		if method in ("users.get", "messages.get", "messages.send"):
    #     #			print "method %s with values %s" % (method, str(values))
    #     #			print "response for method %s: %s" % (method, str(body))
    #     if "response" in body:
    #         return body["response"]
    #
    #     # error processing
    #     error = body["error"]
    #     code = error["error_code"]
    #     # TODO: Check this code
    #     if code == 5:     # invalid token
    #         self.attempts += 1
    #         if self.attempts < 3:
    #             retry = self.retry()
    #             if retry:
    #                 self.attempts = 0
    #                 return retry
    #         else:
    #             raise TokenError(error["error_msg"])
    #     if code == 6:     # too fast
    #         time.sleep(3)
    #         return self.method(method, values)
    #     elif code == 5:     # auth failed
    #         raise VkApiError("Logged out")
    #     if code == 7:
    #         raise NotAllowed
    #     elif code == 9:
    #         return {}
    #     if code == 14:     # captcha
    #         if "captcha_sid" in error:
    #             self.captcha = {"sid": error["captcha_sid"], "img": error["captcha_img"]}
    #             raise CaptchaNeeded
    #     raise VkApiError(body["error"])

    # def retry(self):
    #     if self.last_method:
    #         return self.method(*self.last_method)

#
# def login(jid, number, password):
#
#     logger.debug('VKAPI login')
#
#     url = "https://login.vk.com/"
#     values = {"act": "login",
#               "utf8": "1", # check if it needed
#               "email": number,
#               "pass": password
#     }
#
#     rp = RequestProcessor()
#
#     body, response = rp.post(url, values)
#     remix_sid = rp.get_cookie("remixsid")
#
#     if remix_sid:
#         sid = remix_sid
#     elif "sid=" in response.url:
#         raise AuthenticationException("Captcha!")
#     else:
#         raise AuthenticationException("Invalid password")
#
#     if "security_check" in response.url:
#         raise NotImplementedError
        # # TODO: Rewrite
        # # This code should be rewritten! Users from another countries can have problems because of it!
        # security_hash = webtools.regexp(r"security_check.*?hash: '(.*?)'\};", body)[0]
        # code = self.number[2:-2]
        # if len(self.number) == 12:
        #     if not self.number.startswith("+"):
        #         code = self.number[3:-2]        # may be +375123456789
        #
        # elif len(self.number) == 13:            # so we need 1234567
        #     if self.number.startswith("+"):
        #         code = self.number[4:-2]
        #
        # values = {"act": "security_check",
        #           "al": "1",
        #           "al_page": "3",
        #           "code": code,
        #           "hash": security_hash,
        #           "to": ""
        # }
        # post = self.rp.post("https://vk.com/login.php", values)
        # body, response = post
        # if response and not body.split("<!>")[4] == "4":
        #     raise AuthenticationException("Incorrect number")
#
# def get_token():
#         logger.debug('confirming application')
#
#         url = "https://oauth.vk.com/authorize"
#         values = {"display": "mobile",
#                   "scope": APP_SCOPE,
#                   "client_id": APP_ID,
#                   "response_type": "token",
#                   "redirect_uri": "https://oauth.vk.com/blank.html"
#         }
#
#         rp = RequestProcessor()
#
#         body, response = rp.get(url, values)
#
#         if not response:
#             return
#
#         if "access_token" in response.url:
#             return response.url.split("=")[1].split("&")[0]
#         else:
#             target = webtools.getTagArg("form method=\"post\"", "action", body, "form")
#             if target:
#                 body, response = rp.post(target)
#                 return response.url.split("=")[1].split("&")[0]
#             else:
#                 raise AuthenticationException("Couldn't execute confirmThisApp()!")


def method_wrapped(jid, m, m_args=None):
    """

    @type jid: unicode
    @param jid: client jid
    @param m: method name
    @param m_args: method arguments
    @return: @raise NotImplementedError:
    """
    m_args = m_args or {}

    assert isinstance(jid, unicode)
    assert isinstance(m, unicode)
    assert isinstance(m_args, dict)

    result = {}

    # TODO: Captcha too
    if not realtime.is_user_online(jid):
        return result

    try:
        result = method(m, jid, m_args)
    except CaptchaNeeded:
        logger.error("VKLogin: running captcha challenge for %s" % jid)
        # TODO: Captcha
        raise NotImplementedError('Captcha')
    except NotAllowed:
        # if self.engine.lastMethod[0] == "messages.send":
        messaging.send(jid, "You're not allowed to perform this action.",
                get_friend_jid(m_args.get("user_id", TRANSPORT_ID)))
    except APIError as vk_e:
        if vk_e.message == "User authorization failed: user revoke access for this token.":
            try:
                logger.critical("VKLogin: %s" % vk_e.message)
                database.remove_user(jid)
                database.remove_online_user(jid)
            except KeyError:
                pass
        elif vk_e.message == "User authorization failed: invalid access_token.":
            messaging.send(jid, vk_e.message + " Please, register again", TRANSPORT_ID)
        realtime.set_offline(jid)

        logger.error("VKLogin: apiError %s for user %s" % (vk_e.message, jid))
    return result


def is_application_user(jid):
    """
    Check if client is application user and validate token
    @type jid: unicode
    @param jid: client jid
    @return:
    """
    logger.debug('login api: checking token')

    assert isinstance(jid, unicode)

    try:
        method_wrapped(jid, "isAppUser")
        logger.debug('token for %s is valud' % jid)
        return True
    except AuthenticationException as auth_e:
        logger.debug('checking token failed: %s' % auth_e)
        return False


def mark_messages_as_read(jid, msg_list):
    method("messages.markAsRead", jid, {"message_ids": ','.join(msg_list)})


def get_messages(jid, count=5, last_msg_id=None):
    logger.debug('getting messages for %s' % jid)
    arguments = {"out": 0, "filters": 1, "count": count}
    if last_msg_id:
        arguments.update({'last_message_id': last_msg_id})
    else:
        arguments.update({'count': count})
    return method("messages.get", jid, arguments)