import logging
logger = logging.getLogger("vk4xmpp")
import library.vkapi as api
from sender import Sender

from handlers.message import msg_send, escape_name
from library.writer import dump_crash
from vk2xmpp import vk2xmpp
from config import TRANSPORT_ID
import library.xmpp as xmpp
from library.stext import _ as _
# import handlers.IQ as IQ
from hashlib import sha1
import urllib


def vcard_get_photo(self, url, encode=True):
    try:
        opener = urllib.urlopen(url)
        data = opener.read()
        if data and encode:
            data = data.encode("base64")
        return data
    except IOError:
        pass
    except:
        dump_crash("vcard.getPhoto")


class VKLogin(object):
    def __init__(self, gateway, number, password=None, jid_from=None):
        self.number = number
        self.password = password
        self.gateway = gateway
        self.is_online = False
        self.jid_from = jid_from
        logger.debug("VKLogin.__init__ with number:%s from jid:%s" % (number, jid_from))
        self.engine = None

    # noinspection PyShadowingNames,PyBroadException
    def auth(self, token=None):
        logger.debug("VKLogin.auth %s token" % ("with" if token else "without"))
        try:
            self.engine = api.APIBinding(self.number, self.password, token=token)
            self.check_data()
        except api.AuthError as e:
            logger.error("VKLogin.auth failed with error %s" % e.message)
            return False
        except Exception as e:
            dump_crash("VKLogin.auth")
        logger.debug("VKLogin.auth completed")
        self.is_online = True
        return self.is_online

    def check_data(self):
        if not self.engine.token and self.password:
            logger.debug("VKLogin.checkData: trying to login via password")
            self.engine.loginByPassword()
            self.engine.confirmThisApp()
            if not self.check_token():
                raise api.VkApiError("Incorrect phone or password")

        elif self.engine.token:
            logger.debug("VKLogin.checkData: trying to use token")
            if not self.check_token():
                logger.error("VKLogin.checkData: token invalid: " % self.engine.token)
                raise api.TokenError("Token %s for user %s invalid: " % (self.jid_from, self.engine.token))
        else:
            logger.error("VKLogin.checkData: no token and password for jid:%s" % self.jid_from)
            raise api.TokenError("%s, Where are your token?" % self.jid_from)

    def check_token(self):
        try:
            self.method("isAppUser")
        except api.VkApiError:
            return False
        return True

    def method(self, method, m_args=None):
        m_args = m_args or {}
        result = {}
        if not self.engine.captcha and self.is_online:
            try:
                result = self.engine.method(method, m_args)
            except api.CaptchaNeeded:
                logger.error("VKLogin: running captcha challenge for %s" % self.jid_from)
                self.captcha_challenge()
            except api.NotAllowed:
                if self.engine.lastMethod[0] == "messages.send":
                    msg_send(self.gateway.component, self.jid_from, _("You're not allowed to perform this action."),
                            vk2xmpp(m_args.get("user_id", TRANSPORT_ID)))
            except api.VkApiError as vk_e:
                if vk_e.message == "User authorization failed: user revoke access for this token.":
                    try:
                        logger.critical("VKLogin: %s" % vk_e.message)
                        self.gateway.clients[self.jid_from].delete_user()
                    except KeyError:
                        pass
                elif vk_e.message == "User authorization failed: invalid access_token.":
                    msg_send(self.gateway.component, self.jid_from, _(vk_e.message + " Please, register again"), TRANSPORT_ID)
                self.is_online = False
                logger.error("VKLogin: apiError %s for user %s" % (vk_e.message, self.jid_from))
        return result

    def captcha_challenge(self):
        if self.engine.captcha:
            logger.debug("VKLogin: sending message with captcha to %s" % self.jid_from)
            body = _("WARNING: VK sent captcha to you."
                     " Please, go to %s and enter text from image to chat."
                     " Example: !captcha my_captcha_key. Tnx") % self.engine.captcha["img"]
            captcha_message = xmpp.Message(self.jid_from, body, "chat", frm=TRANSPORT_ID)
            x_tag = captcha_message.setTag("x", {}, xmpp.NS_OOB)
            x_tag.setTagData("url", self.engine.captcha["img"])
            c_tag = captcha_message.setTag("captcha", {}, xmpp.NS_CAPTCHA)
            img = vcard_get_photo(self.engine.captcha["img"], False)
            if img:
                img_hash = sha1(img).hexdigest()
                img_encoded = img.encode("base64")
                form = xmpp.DataForm("form")
                form.setField("FORM_TYPE", xmpp.NS_CAPTCHA, "hidden")
                form.setField("from", TRANSPORT_ID, "hidden")
                field = form.setField("ocr")
                field.setLabel(_("Enter shown text"))
                field.delAttr("type")
                field.setPayload([xmpp.Node("required"),
                                  xmpp.Node("media", {"xmlns": xmpp.NS_MEDIA},
                                            [xmpp.Node("uri", {"type": "image/jpg"},
                                                       ["cid:sha1+%s@bob.xmpp.org" % img_hash])])])
                c_tag.addChild(node=form)
                ob_tag = captcha_message.setTag("data",
                                               {"cid": "sha1+%s@bob.xmpp.org" % img_hash, "type": "image/jpg",
                                                "max-age": "0"},
                                               xmpp.NS_URN_OOB)
                ob_tag.setData(img_encoded)
            else:
                logger.critical("VKLogin: can't add captcha image to message url:%s" % self.engine.captcha["img"])
            self.gateway.send(captcha_message)
            presence = xmpp.protocol.Presence(self.jid_from, frm=TRANSPORT_ID)
            presence.setStatus(body)
            presence.setShow("xa")
            self.gateway.send(presence)
        else:
            logger.error("VKLogin: captchaChallenge called without captcha for user %s" % self.jid_from)

    def disconnect(self):
        logger.debug("VKLogin: user %s has left" % self.jid_from)
        self.method("account.setOffline")
        self.is_online = False

    def get_token(self):
        return self.engine.token

    def get_friends(self, fields=None):
        fields = fields or ["screen_name"]
        friends_raw = self.method("friends.get", {"fields": ",".join(fields)}) or {} # friends.getOnline
        friends = {}
        for friend in friends_raw:
            uid = friend["uid"]
            name = escape_name("", u"%s %s" % (friend["first_name"], friend["last_name"]))
            try:
                friends[uid] = {"name": name, "online": friend["online"]}
                for key in fields:
                    if key != "screen_name":
                        friends[uid][key] = friend.get(key)
            except KeyError as key_error:
                logger.debug('%s while processing %s' % (key_error, uid))
                continue
        return friends

    def msg_mark_as_read(self, msg_list):
        msg_list = str.join(",", msg_list)
        self.method("messages.markAsRead", {"message_ids": msg_list})

    def get_messages(self, count=5, last_msg_id=0):
        values = {"out": 0, "filters": 1, "count": count}
        if last_msg_id:
            del values["count"]
            values["last_message_id"] = last_msg_id
        return self.method("messages.get", values)
