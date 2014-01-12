# /* coding: utf-8 */
# © simpleApps CodingTeam, 2013.
# Warning: Code in this module is ugly,
# but we can't do better.

import time, ssl, urllib, urllib2, cookielib
import logging, json, webtools


logger = logging.getLogger("vk4xmpp")


def attemptTo(maxRetries, resultType, *errors):
    """
    Tries to execute function ignoring specified errors specified number of
    times and returns specified result type on try limit.
    """
    if not isinstance(resultType, type):
        resultType = lambda result=resultType: result
    if not errors:
        errors = Exception

    def decorator(func):

        def wrapper(*args, **kwargs):
            retries = 0
            while retries < maxRetries:
                try:
                    data = func(*args, **kwargs)
                except errors as exc:
                    retries += 1
                    time.sleep(0.2)
                else:
                    break
            else:
                data = resultType()
                logger.debug("Error %s occured on executing %s" % (exc, func))
            return data

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


class RequestProcessor(object):
    """
    Processing base requests: POST (multipart/form-data) and GET.
    """
    headers = {"User-agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:21.0)"
                             " Gecko/20130309 Firefox/21.0",
               "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
               "Accept-Language": "ru-RU, utf-8"
    }

    def __init__(self):
        self.cookieJar = cookielib.CookieJar()
        self.cookieProcessor = urllib2.HTTPCookieProcessor(self.cookieJar)
        self.open = urllib2.build_opener(self.cookieProcessor).open
        self.open.im_func.func_defaults = (None, 4)

    def getCookie(self, name):
        for cookie in self.cookieJar:
            if cookie.name == name:
                return cookie.value

    def request(self, url, data=None, headers=None):
        headers = headers or self.headers
        if data:
            data = urllib.urlencode(data)
        request = urllib2.Request(url, data, headers)
        return request

    @attemptTo(5, dict, urllib2.URLError, ssl.SSLError)
    def post(self, url, data={}):
        resp = self.open(self.request(url, data))
        body = resp.read()
        return (body, resp)

    @attemptTo(5, dict, urllib2.URLError, ssl.SSLError)
    def get(self, url, query={}):
        if query:
            url += "/?%s" % urllib.urlencode(query)
        resp = self.open(self.request(url))
        body = resp.read()
        return (body, resp)     # I'd like brackets. Why not?


class APIBinding:
    def __init__(self, number, password=None, token=None, app_id=3789129,
                 scope=69634):
        self.password = password
        self.number = number

        self.sid = None
        self.token = token
        self.captcha = {}
        self.last = []
        self.lastMethod = None

        self.app_id = app_id
        self.scope = scope

        self.RIP = RequestProcessor()
        self.attempts = 0

    def loginByPassword(self):
        url = "https://login.vk.com/"
        values = {"act": "login",
                  "utf8": "1", # check if it needed
                  "email": self.number,
                  "pass": self.password
        }

        body, response = self.RIP.post(url, values)
        remixSID = self.RIP.getCookie("remixsid")

        if remixSID:
            self.sid = remixSID

        elif "sid=" in response.url:
            raise AuthError("Captcha!")
        else:
            raise AuthError("Invalid password")

        if "security_check" in response.url:
            # This code should be rewritten! Users from another countries can have problems because of it!
            Hash = webtools.regexp(r"security_check.*?hash: '(.*?)'\};", body)[0]
            code = self.number[2:-2]
            if len(self.number) == 12:
                if not self.number.startswith("+"):
                    code = self.number[3:-2]        # may be +375123456789

            elif len(self.number) == 13:            # so we need 1234567
                if self.number.startswith("+"):
                    code = self.number[4:-2]

            values = {"act": "security_check",
                      "al": "1",
                      "al_page": "3",
                      "code": code,
                      "hash": Hash,
                      "to": ""
            }
            post = self.RIP.post("https://vk.com/login.php", values)
            body, response = post
            if response and not body.split("<!>")[4] == "4":
                raise AuthError("Incorrect number")

    def checkSid(self):
        if self.sid:
            url = "https://vk.com/feed2.php"
            get = self.RIP.get(url)
            body, response = get
            if body and response:
                data = json.loads(body)
                if data["user"]["id"] != -1:
                    return data

    def confirmThisApp(self):
        url = "https://oauth.vk.com/authorize"
        values = {"display": "mobile",
                  "scope": self.scope,
                  "client_id": self.app_id,
                  "response_type": "token",
                  "redirect_uri": "https://oauth.vk.com/blank.html"
        }

        token = None
        body, response = self.RIP.get(url, values)
        if response:
            if "access_token" in response.url:
                token = response.url.split("=")[1].split("&")[0]
            else:
                postTarget = webtools.getTagArg("form method=\"post\"", "action", body, "form")
                if postTarget:
                    body, response = self.RIP.post(PostTarget)
                    token = response.url.split("=")[1].split("&")[0]
                else:
                    raise AuthError("Couldn't execute confirmThisApp()!")
        self.token = token


    def method(self, method, values=None):
        values = values or {}
        url = "https://api.vk.com/method/%s" % method
        values["access_token"] = self.token
        values["v"] = "3.0"

        if self.captcha and self.captcha.has_key("key"):
            values["captcha_sid"] = self.captcha["sid"]
            values["captcha_key"] = self.captcha["key"]
            self.captcha = {}
        self.lastMethod = (method, values)
        self.last.append(time.time())
        if len(self.last) > 2:
            if (self.last.pop() - self.last.pop(0)) < 1.1:
                time.sleep(0.3)    # warn: it was 0.4 // does it matter?

        response = self.RIP.post(url, values)
        if response:
            body, response = response
            if body:
                body = json.loads(body)
                # Debug:
            #		if method in ("users.get", "messages.get", "messages.send"):
            #			print "method %s with values %s" % (method, str(values))
            #			print "response for method %s: %s" % (method, str(body))
            if "response" in body:
                return body["response"]

            elif "error" in body:
                error = body["error"]
                eCode = error["error_code"]
                ## TODO: Check this code
                if eCode == 5:     # invalid token
                    self.attempts += 1
                    if self.attempts < 3:
                        retry = self.retry()
                        if retry:
                            self.attempts = 0
                            return retry
                    else:
                        raise TokenError(error["error_msg"])
                if eCode == 6:     # too fast
                    time.sleep(3)
                    return self.method(method, values)
                elif eCode == 5:     # auth failed
                    raise VkApiError("Logged out")
                if eCode == 7:
                    raise NotAllowed
                elif eCode == 9:
                    return {}
                if eCode == 14:     # captcha
                    if "captcha_sid" in error:
                        self.captcha = {"sid": error["captcha_sid"], "img": error["captcha_img"]}
                        raise CaptchaNeeded
                raise VkApiError(body["error"])

    def retry(self):
        if self.lastMethod:
            return self.method(*self.lastMethod)


class VkApiError(Exception):
    pass


class AuthError(VkApiError):
    pass


class CaptchaNeeded(VkApiError):
    pass


class TokenError(VkApiError):
    pass


class NotAllowed(VkApiError):
    pass
