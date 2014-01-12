# coding: utf-8
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

import logging
import urllib
import os
import sys
import time

from library.writer import dump_crash
import config
import library.xmpp as xmpp
from sender import Sender
import library.vkapi as api
from handler import Handler
from message import MessageHandler
from message import watcher_msg
from library.itypes import Database
from library.stext import _ as _
from vk2xmpp import vk2xmpp
from user import TUser


logger = logging.getLogger("vk4xmpp")


class IQHandler(Handler):
    sDict = {
        "users/total": "users",
        "users/online": "users",
        "memory/virtual": "KB",
        "memory/real": "KB",
        "cpu/percent": "percent",
        "cpu/time": "seconds"
    }

    def __init__(self, gateway):
        super(IQHandler, self).__init__(gateway)

    def handle(self, cl, iq):
        jid_from = iq.getFrom()
        jid_from_str = jid_from.getStripped()
        if config.WHITE_LIST:
            if jid_from and jid_from.getDomain() not in config.WHITE_LIST:
                Sender(cl, self.iq_build_error(iq, xmpp.ERR_BAD_REQUEST, "You're not in the white-list"))
                raise xmpp.NodeProcessed()

        if iq.getType() == "set" and iq.getTagAttr("captcha", "xmlns") == xmpp.NS_CAPTCHA:
            if jid_from_str in self.clients:
                jid_to = iq.getTo()
                if jid_to == config.TRANSPORT_ID:
                    c_tag = iq.getTag("captcha")
                    cx_tag = c_tag.getTag("x", {}, xmpp.NS_DATA)
                    fcx_tag = cx_tag.getTag("field", {"var": "ocr"})
                    c_value = fcx_tag.getTagData("value")
                    MessageHandler.captcha_accept(self, cl, c_value, jid_to, jid_from_str)

        ns = iq.getQueryNS()
        if ns == xmpp.NS_REGISTER:
            self.iq_register_handler(cl, iq)
        elif ns == xmpp.NS_GATEWAY:
            self.iq_gateway_handler(cl, iq)
        elif ns == xmpp.NS_STATS:
            self.iqStatsHandler(cl, iq)
        elif ns == xmpp.NS_VERSION:
            self.iqVersionHandler(cl, iq)
        elif ns == xmpp.NS_LAST:
            self.iq_uptime_handler(cl, iq)
        elif ns in (xmpp.NS_DISCO_INFO, xmpp.NS_DISCO_ITEMS):
            self.iq_disco_handler(cl, iq)
        else:
            tag = iq.getTag("vCard") or iq.getTag("ping")
            if tag and tag.getNamespace() == xmpp.NS_VCARD:
                self.iq_vcard_handler(cl, iq)
            elif tag and tag.getNamespace() == xmpp.NS_PING:
                jid_to = iq.getTo()
                if jid_to == config.TRANSPORT_ID:
                    Sender(cl, iq.buildReply("result"))

        raise xmpp.NodeProcessed()

    def iq_build_error(self, stanza, error=None, text=None):
        if not error:
            error = xmpp.ERR_FEATURE_NOT_IMPLEMENTED
        error = xmpp.Error(stanza, error, True)
        if text:
            etag = error.getTag("error")
            etag.setTagData("text", text)
        return error


    def iq_register_handler(self, cl, iq):
        jid_to = iq.getTo()
        jid_from = iq.getFrom()
        jid_from_str = jid_from.getStripped()
        jid_to_str = jid_to.getStripped()
        iq_type = iq.getType()
        iq_children = iq.getQueryChildren()
        result = iq.buildReply("result")
        if config.USER_LIMIT:
            count = self.calc_stats()[0]
            if count >= config.USER_LIMIT and not jid_from_str in self.clients:
                cl.send(self.iq_build_error(iq, xmpp.ERR_NOT_ALLOWED,
                                            _("Transport's admins limited registrations, sorry.")))
                raise xmpp.NodeProcessed
        if iq_type == "get" and jid_to_str == config.TRANSPORT_ID and not iq_children:
            form = xmpp.DataForm()
            logger.debug("Sending register form to %s" % jid_from_str)
            form.addChild(node=xmpp.Node("instructions")).setData(_("Type data in fields"))
            link = form.setField("link", config.URL_ACCEPT_APP)
            link.setLabel(_("Autorization page"))
            link.setDesc(
                _("If you won't get access-token automatically, please, follow authorization link and authorize app,\n" \
                  "and then paste url to password field."))
            phone = form.setField("phone", "+")
            phone.setLabel(_("Phone number"))
            phone.setDesc(_("Enter phone number in format +71234567890"))
            use_password = form.setField("use_password", "0", "boolean")
            use_password.setLabel(_("Get access-token automatically"))
            use_password.setDesc(_("Try to get access-token automatically. (NOT recommented, password required!)"))
            password = form.setField("password", None, "text-private")
            password.setLabel(_("Password/Access-token"))
            password.setType("text-private")
            password.setDesc(_("Type password, access-token or url (recommented)"))
            result.setQueryPayload((form,))

        elif iq_type == "set" and jid_to_str == config.TRANSPORT_ID and iq_children:
            phone, password, use_password, token = False, False, False, False
            query = iq.getTag("query")
            if query.getTag("x"):
                for node in iq.getTags("query", namespace=xmpp.NS_REGISTER):
                    for node in node.getTags("x", namespace=xmpp.NS_DATA):
                        phone = node.getTag("field", {"var": "phone"})
                        phone = phone and phone.getTagData("value")
                        password = node.getTag("field", {"var": "password"})
                        password = password and password.getTagData("value")
                        use_password = node.getTag("field", {"var": "use_password"})
                        use_password = use_password and use_password.getTagData("value")

                if not password:
                    result = self.iq_build_error(iq, xmpp.ERR_BAD_REQUEST, _("Null password"))

                is_number = True
                try:
                    use_password = int(use_password)
                except ValueError:
                    if use_password and use_password.lower() == "true":
                        use_password = 1
                    else:
                        use_password = 0

                if not use_password:
                    logger.debug("user %s won't to use password" % jid_from_str)
                    token = password
                    password = None
                else:
                    logger.debug("user %s want to use password" % jid_from_str)
                    if not phone:
                        result = self.iq_build_error(iq, xmpp.ERR_BAD_REQUEST, _("Phone incorrect."))
                if jid_from_str in self.clients:
                    user = self.clients[jid_from_str]
                    user.delete_user()
                else:
                    user = TUser(self.gateway, (phone, password), jid_from_str)
                if not use_password:
                    try:
                        token = token.split("#access_token=")[1].split("&")[0].strip()
                    except (IndexError, AttributeError):
                        pass
                    user.token = token
                if not user.connect():
                    logger.error("user %s connection failed (from iq)" % jid_from_str)
                    result = self.iq_build_error(iq, xmpp.ERR_BAD_REQUEST, _("Incorrect password or access token!"))
                else:
                    try:
                        user.init()
                    except api.CaptchaNeeded:
                        user.vk.captcha_challenge()
                    except:
                        dump_crash("iq.user.init")
                        result = self.iq_build_error(iq, xmpp.ERR_BAD_REQUEST, _("Initialization failed."))
                    else:
                        self.clients[jid_from_str] = user
                        self.gateway.update_transports_list(self.clients[jid_from_str])
                        watcher_msg(_("New user registered: %s") % jid_from_str)

            elif query.getTag("remove"): # Maybe exits a better way for it
                logger.debug("user %s want to remove me :(" % jid_from_str)
                if jid_from_str in self.clients:
                    client = self.clients[jid_from_str]
                    client.delete_user(True)
                    result.setPayload([], add=0)
                    self.clients(_("User removed registration: %s") % jid_from_str)
            else:
                result = self.iq_build_error(iq, 0, _("Feature not implemented."))
        Sender(cl, result)

    def calc_stats(self):
        count_total = 0
        count_online = 0
        # TODO: Semaphore
        with Database(config.DB_FILE) as db:
            db("select count(*) from users")
            count_total = db.fetchone()[0]
        for key in self.clients:
            if hasattr(key, "vk") and key.vk.Online:
                count_online += 1
        return [count_total, count_online]

    def iq_uptime_handler(self, cl, iq):
        jidFrom = iq.getFrom()
        jidTo = iq.getTo()
        iType = iq.getType()
        if iType == "get" and jidTo == config.TRANSPORT_ID:
            uptime = int(time.time() - self.gateway.start_time)
            result = xmpp.Iq("result", to=jidFrom)
            result.setID(iq.getID())
            result.setTag("query", {"seconds": str(uptime)}, xmpp.NS_LAST)
            result.setTagData("query", config.IDENTIFIER["name"])
            Sender(cl, result)
        raise xmpp.NodeProcessed()


    def iqVersionHandler(self, cl, iq):
        iType = iq.getType()
        jidTo = iq.getTo()
        if iType == "get" and jidTo == config.TRANSPORT_ID:
            result = iq.buildReply("result")
            Query = result.getTag("query")
            Query.setTagData("name", config.IDENTIFIER["name"])
            os_name = "{0} {2:.16} [{4}]".format(*os.uname())
            python_version = "{0} {1}.{2}.{3}".format(sys.subversion[0], *sys.version_info)
            # TODO: WTF
            Query.setTagData("version", 666)
            Query.setTagData("os", "%s / %s" % (os_name, python_version))
            Sender(cl, result)
        raise xmpp.NodeProcessed()

    def iqStatsHandler(self, cl, iq):
        jid_to_str = iq.getTo()
        i_type = iq.getType()
        iq_children = iq.getQueryChildren()
        result = iq.buildReply("result")
        if i_type == "get" and jid_to_str == config.TRANSPORT_ID:
            querypayload = list()
            if not iq_children:
                keys = sorted(self.sDict.keys(), reverse=True)
                for key in keys:
                    Node = xmpp.Node("stat", {"name": key})
                    querypayload.append(Node)
            else:
                users = self.calc_stats()
                shell = os.popen("ps -o vsz,rss,%%cpu,time -p %s" % os.getpid()).readlines()
                memVirt, memReal, cpuPercent, cpuTime = shell[1].split()
                stats = {"users": users, "KB": [memVirt, memReal],
                         "percent": [cpuPercent], "seconds": [cpuTime]}
                for Child in iq_children:
                    if Child.getName() != "stat":
                        continue
                    name = Child.getAttr("name")
                    if name in self.sDict:
                        attr = self.sDict[name]
                        value = stats[attr].pop(0)
                        Node = xmpp.Node("stat", {"units": attr})
                        Node.setAttr("name", name)
                        Node.setAttr("value", value)
                        querypayload.append(Node)
            if querypayload:
                result.setQueryPayload(querypayload)
                Sender(cl, result)

    def iq_disco_handler(self, cl, iq):
        jid_from_str = iq.getFrom().getStripped()
        jid_to_str = iq.getTo().getStripped()
        iq_type = iq.getType()
        ns = iq.getQueryNS()
        node = iq.getTagAttr("query", "node")
        if iq_type == "get":
            if not node and jid_to_str == config.TRANSPORT_ID:
                querypayload = []
                result = iq.buildReply("result")
                querypayload.append(xmpp.Node("identity", config.IDENTIFIER))
                if ns == xmpp.NS_DISCO_INFO:
                    for key in self.gateway.features:
                        xNode = xmpp.Node("feature", {"var": key})
                        querypayload.append(xNode)
                    result.setQueryPayload(querypayload)
                elif ns == xmpp.NS_DISCO_ITEMS:
                    result.setQueryPayload(querypayload)
                Sender(cl, result)
        raise xmpp.NodeProcessed()


    def iq_gateway_handler(self, cl, iq):
        jid_to = iq.getTo()
        i_type = iq.getType()
        jid_to_str = jid_to.getStripped()
        iq_children = iq.getQueryChildren()

        if jid_to_str == config.TRANSPORT_ID:
            result = iq.buildReply("result")
            if i_type == "get" and not iq_children:
                query = xmpp.Node("query", {"xmlns": xmpp.NS_GATEWAY})
                query.setTagData("desc", "Enter phone number")
                query.setTag("prompt")
                result.setPayload([query])

            elif iq_children and i_type == "set":
                phone = ""
                for node in iq_children:
                    if node.getName() == "prompt":
                        phone = node.getData()
                        break
                if phone:
                    xNode = xmpp.simplexml.Node("prompt")
                    xNode.setData(phone[0])
                    result.setQueryPayload([xNode])
            else:
                raise xmpp.NodeProcessed()
            Sender(cl, result)


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


    def iq_vcard_build(self, tags):
        vcard = xmpp.Node("vCard", {"xmlns": xmpp.NS_VCARD})
        for key in tags.keys():
            if key == "PHOTO":
                bval = vcard.setTag("PHOTO")
                bval.setTagData("BINVAL", self.vcard_get_photo(tags[key]))
            else:
                vcard.setTagData(key, tags[key])
        return vcard

    def iq_vcard_handler(self, cl, iq):
        jid_from = iq.getFrom()
        jid_to = iq.getTo()
        jid_from_str = jid_from.getStripped()
        jid_to_str = jid_to.getStripped()
        i_type = iq.getType()
        result = iq.buildReply("result")
        if i_type == "get":
            _DESC = '\n'.join(
                (config.DESC, "_" * 16, config.ADDITIONAL_ABOUT)) if config.ADDITIONAL_ABOUT else config.DESC
            if jid_to_str == config.TRANSPORT_ID:
                vcard = self.iq_vcard_build({"NICKNAME": "VK4XMPP Transport",
                                             "DESC": _DESC,
                                             "PHOTO": "https://raw.github.com/mrDoctorWho/vk4xmpp/master/vk4xmpp.png",
                                             "URL": "http://simpleapps.ru"})
                result.setPayload([vcard])

            elif jid_from_str in self.clients:
                c = self.clients[jid_from_str]
                if c.friends:
                    jid = vk2xmpp(jid_to_str)
                    json = c.get_user_data(jid, ["screen_name", config.PHOTO_SIZE])
                    values = {"NICKNAME": json.get("name", str(json)),
                              "URL": "http://vk.com/id%s" % jid,
                              "DESC": _("Contact uses VK4XMPP Transport\n%s") % _DESC}
                    if jid in c.friends.keys():
                        values["PHOTO"] = json.get(config.PHOTO_SIZE) or config.URL_VCARD_NO_IMAGE
                    vcard = self.iq_vcard_build(values)
                    result.setPayload([vcard])
                else:
                    result = self.iq_build_error(iq, xmpp.ERR_BAD_REQUEST, _("Your friend-list is null."))
            else:
                result = self.iq_build_error(iq, xmpp.ERR_REGISTRATION_REQUIRED,
                                             _("You're not registered for this action."))
        else:
            raise xmpp.NodeProcessed()
        Sender(cl, result)


def get_handler(gateway):
    return IQHandler(gateway).handle