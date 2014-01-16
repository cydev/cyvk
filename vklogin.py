import logging

from friends import get_friend_jid
import vkapi as api
from messaging import send_message, escape_name
from config import TRANSPORT_ID
# from stext import _ as _
import database
from vkapi import method, method_wrapped
from errors import AuthenticationException, APIError, TokenError, CaptchaNeeded, NotAllowed


logger = logging.getLogger("vk4xmpp")

# def vcard_get_photo(self, url, encode=True):
#     try:
#         opener = urllib.urlopen(url)
#         data = opener.read()
#         if data and encode:
#             data = data.encode("base64")
#         return data
#     except IOError as e:
#         logging.error('IOError while vcard_get_photo: %s' % e)
#         return None
#     # except:
    #     dump_crash("vcard.getPhoto")


class VKLogin(object):
    def __init__(self, gateway, token, jid):
        self.gateway = gateway
        self.is_online = False
        self.jid = jid
        logger.debug("VKLogin init")
        self.engine = None
        self.token = token

    # noinspection PyShadowingNames,PyBroadException
    def auth(self, jid, token=None):
        # print 'auth', jid, token
        self.jid = jid
        self.token = token or self.token
        logger.debug('Token: %s' % token)
        logger.debug("VKLogin.auth %s token" % ("with" if token else "without"))
        try:
            self.engine = api.APIBinding(token)
            self.check_data()
        except AuthenticationException as e:
            logger.error("VKLogin.auth failed with error %s" % e.message)
            return False
        logger.debug("VKLogin.auth completed")
        self.is_online = True
        return self.is_online

    def check_data(self):
        # if not self.token and self.password:
        #     logger.debug("VKLogin.checkData: trying to login via password")
        #     self.engine.login()
        #     self.engine.confirm()
        #     if not self.check_token():
        #         raise APIError("Incorrect phone or password")

        # elif self.engine.token:
        if not self.token:
            raise TokenError('no token for %s' % self.jid)

        logger.debug("VKLogin.checkData: using token")
        if not self.check_token():
            logger.error("VKLogin.checkData: token invalid: " % self.engine.token)
            raise TokenError("Token %s for user %s invalid: " % (self.jid, self.engine.token))
    # else:
    #         logger.error("VKLogin.checkData: no token and password for jid:%s" % self.jid_from)
    #         raise TokenError("%s, Where are your token?" % self.jid_from)

    def check_token(self):
        try:
            method_wrapped(self.gateway, self.jid, "isAppUser")
        except APIError:
            return False
        return True

    def method(self, m, m_args=None):
        if not self.jid:
            raise ValueError('jid is None')

        jid = self.jid
        gateway = self.gateway

        m_args = m_args or {}
        result = {}
        # if self.engine.captcha or not self.is_online:
        #     return result

        if not database.is_user_online(jid):
            return result

        try:
            result = method(m, jid, m_args)
        except CaptchaNeeded:
            logger.error("VKLogin: running captcha challenge for %s" % jid)
            # TODO: Captcha
            raise NotImplementedError('Captcha')
        except NotAllowed:
            # if self.engine.lastMethod[0] == "messages.send":
            send_message(gateway.component, jid, "You're not allowed to perform this action.",
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
                send_message(gateway.component, jid, vk_e.message + " Please, register again"), TRANSPORT_ID
            database.set_offline(jid)

            logger.error("VKLogin: apiError %s for user %s" % (vk_e.message, jid))
        return result

    def disconnect(self):
        logger.debug("VKLogin: user %s has left" % self.jid)
        m = "account.setOffline"
        # TODO: async
        method(m, self.jid)
        database.set_offline(self.jid)

    def get_token(self):
        return self.engine.token

    def get_friends(self, fields=None):
        fields = fields or ["screen_name"]
        friends_raw = self.method("friends.get", {"fields": ",".join(fields)}) or {} # friends.getOnline
        print 'Friends raw: %s' % friends_raw
        friends = {}
        for friend in friends_raw:
            uid = friend["uid"]
            name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
            friends[uid] = {"name": name, "online": friend["online"]}
            for key in fields:
                if key != "screen_name":
                    friends[uid][key] = friend.get(key)
        return friends

    def msg_mark_as_read(self, msg_list):
        msg_list = str.join(",", msg_list)
        self.method("messages.markAsRead", {"message_ids": msg_list})

    # def get_messages(self, count=5, last_msg_id=0):
    #     values = {"out": 0, "filters": 1, "count": count}
    #     if last_msg_id:
    #         del values["count"]
    #         values["last_message_id"] = last_msg_id
    #     return self.method("messages.get", values)














# def check_data(jid, token, password=None):
#     if not jid:
#         raise ValueError('no jid')
#
#     if not token and password:
#         logger.debug("VKLogin.checkData: trying to login via password")
#         self.engine.login()
#         self.engine.confirm()
#         if not self.check_token():
#             raise APIError("Incorrect phone or password")
#
#     elif self.engine.token:
#         logger.debug("VKLogin.checkData: trying to use token")
#         if not self.check_token():
#             logger.error("VKLogin.checkData: token invalid: " % self.engine.token)
#             raise TokenError("Token %s for user %s invalid: " % (self.jid_from, self.engine.token))
#     else:
#         logger.error("VKLogin.checkData: no token and password for jid:%s" % self.jid_from)
#         raise TokenError("%s, Where are your token?" % self.jid_from)

#
# def auth(self, jid, token=None):
#     logger.debug('Token: %s' % token)
#     logger.debug("VKLogin.auth %s token" % ("with" if token else "without"))
#     try:
#         self.engine = api.APIBinding(self.number, self.password, token=token)
#         self.check_data()
#     except AuthenticationException as e:
#         logger.error("VKLogin.auth failed with error %s" % e.message)
#         return False
#     logger.debug("VKLogin.auth completed")
#     self.is_online = True
#     return self.is_online
