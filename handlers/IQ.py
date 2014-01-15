# coding: utf-8

import logging
import urllib

import config
from config import WHITE_LIST, IDENTIFIER, TRANSPORT_ID
from friends import get_friend_jid
from library.xmpp.protocol import (NodeProcessed, NS_REGISTER, NS_CAPTCHA, NS_GATEWAY,
                                   NS_DISCO_ITEMS, NS_DISCO_INFO, NS_VCARD, NS_PING, ERR_FEATURE_NOT_IMPLEMENTED,
                                   Error, NS_DATA, ERR_BAD_REQUEST, Node, ERR_REGISTRATION_REQUIRED)

import library.xmpp.simplexml

from sender import stanza_send
from handler import Handler
from messaging import send_watcher_message
from captcha import captcha_accept
import user as user_api
from errors import AuthenticationException
import database
import forms
from singletone import Gateway


logger = logging.getLogger("vk4xmpp")


class IQ(object):
    def __init__(self, iq):
        self.jid_from = iq.getFrom()
        self.jid_to = iq.getTo()
        self.jid_from_str = self.jid_from.getStripped()
        self.jid_to_str = self.jid_to.getStripped()
        self.i_type = iq.getType()
        self.ns = iq.getQueryNS()
        self.node = iq.getTagAttr("query", "node")
        self.result = iq.buildReply("result")
        # self.result_str = self.result.getStripped()

    def __repr__(self):
        return '<IQ %s->%s>' % (self.jid_from_str, self.jid_to_str)


def generate_error(stanza, error=None, text=None):
    if not error:
        error = ERR_FEATURE_NOT_IMPLEMENTED
    error = Error(stanza, error, True)
    if text:
        etag = error.getTag("error")
        etag.setTagData("text", text)
    return error


def _send_form(_, iq, jid):
    logger.debug("sending register form to %s" % jid)
    result = iq.buildReply("result")
    result.setQueryPayload((forms.get_form(),))
    return result


def _process_form(gateway, iq, jid):
    logger.debug('received register form from %s' % jid)

    assert isinstance(gateway, Gateway)
    assert isinstance(jid, unicode)

    result = iq.buildReply("result")

    query = iq.getTag("query")

    token = query.getTag("x").getTag("field", {"var": "password"}).getTagData("value")

    try:
        token = token.split("#access_token=")[1].split("&")[0].strip()
    except (IndexError, AttributeError) as e:
        logger.debug('access token in raw format')

    logger.debug('form processed')

    user_attributes = database.get_description(jid)

    if not user_attributes:
        logger.debug('user %s is not in database' % jid)
        database.insert_user(jid, None, token, None, False)
        # user = TUser(self.gateway, token, jid)
        # user.token = token
    # if not database.is_client(jid):
    #     logger.debug('user %s is not in client list' % jid)
    #
    #     user.token = token
    else:
        raise NotImplementedError('already in database')

    try:
        user_api.connect(gateway, jid, token)
        user_api.initialize(gateway, jid)
    except AuthenticationException:
        logger.error("user %s connection failed (from iq)" % jid)
        result = generate_error(iq, ERR_BAD_REQUEST, "Incorrect password or access token")

    database.set_last_activity_now(jid)
    gateway.add_user(jid)
    send_watcher_message(gateway.component, "new user registered: %s" % jid)
    logger.debug('registration for %s completed' % jid)

    return result


class IQHandler(Handler):
    # sDict = {
    #     "users/total": "users",
    #     "users/online": "users",
    #     "memory/virtual": "KB",
    #     "memory/real": "KB",
    #     "cpu/percent": "percent",
    #     "cpu/time": "seconds"
    # }

    def __init__(self, gateway):
        super(IQHandler, self).__init__(gateway)

    def handle(self, transport, stanza):
        jid_from = stanza.getFrom()
        jid_from_str = jid_from.getStripped()
        jid_to = stanza.getTo()

        if WHITE_LIST and jid_from and jid_from.getDomain() not in WHITE_LIST:
            stanza_send(transport, generate_error(stanza, ERR_BAD_REQUEST, "You are not in white list"))
            raise NodeProcessed()

        from_is_client = database.is_client(jid_from_str)
        destination_is_transport = jid_to == config.TRANSPORT_ID
        ns_is_captcha = stanza.getTagAttr("captcha", "xmlns") == NS_CAPTCHA

        if from_is_client and destination_is_transport and ns_is_captcha:
            c_tag = stanza.getTag("captcha")
            cx_tag = c_tag.getTag("x", {}, NS_DATA)
            fcx_tag = cx_tag.getTag("field", {"var": "ocr"})
            c_value = fcx_tag.getTagData("value")
            captcha_accept(self.gateway, transport, c_value, jid_to, jid_from_str)

        ns = stanza.getQueryNS()

        mapping = {
            NS_REGISTER: self.iq_register_handler,
            NS_GATEWAY: self.iq_gateway_handler,
            NS_DISCO_INFO: self.iq_disco_handler,
            NS_DISCO_ITEMS: self.iq_disco_handler
        }

        try:
            mapping[ns](transport, stanza)
        except KeyError:
            tag = stanza.getTag("vCard") or stanza.getTag("ping")
            if tag and tag.getNamespace() == NS_VCARD:
                self.iq_vcard_handler(transport, stanza)
            elif tag and tag.getNamespace() == NS_PING:
                if jid_to == config.TRANSPORT_ID:
                    stanza_send(transport, stanza.buildReply("result"))

        raise NodeProcessed()


    def iq_register_handler(self, transport, stanza):
        jid = stanza.getFrom().getStripped()
        logger.debug('register handler for %s' % jid)

        destination_jid = stanza.getTo().getStripped()

        logger.debug('destination %s' % destination_jid)
        # iq_type = iq.getType()
        # iq_children = iq.getQueryChildren()
        # result = iq.buildReply("result")
        # if config.USER_LIMIT:
        #     count = self.calc_stats()[0]
        #     if count >= config.USER_LIMIT and not jid_from_str in self.clients:
        #         cl.send(self.iq_build_error(iq, xmpp.ERR_NOT_ALLOWED,
        #                                     _("Transport's admins limited registrations, sorry.")))
        #         raise xmpp.NodeProcessed

        if destination_jid != config.TRANSPORT_ID:
            logger.debug('register not to transport')
            return

        gateway = self.gateway

        try:
            handler = {'get': _send_form, 'set': _process_form}[stanza.getType()]
            stanza_send(transport, handler(gateway, stanza, jid))
        except (NotImplementedError, KeyError) as e:
            stanza_send(transport, generate_error(stanza, 0, "Requested feature not implemented: %s" % e))


    # def calc_stats(self):
    #     count_total = 0
    #     count_online = 0
    #     # TODO: Semaphore
    #     with Database(config.DB_FILE) as db:
    #         db("select count(*) from users")
    #         count_total = db.fetchone()[0]
    #     for key in self.clients:
    #         if hasattr(key, "vk") and key.vk.Online:
    #             count_online += 1
    #     return [count_total, count_online]

    # def iq_uptime_handler(self, cl, iq):
    #     jidFrom = iq.getFrom()
    #     jidTo = iq.getTo()
    #     iType = iq.getType()
    #     if iType == "get" and jidTo == config.TRANSPORT_ID:
    #         uptime = int(time.time() - self.gateway.start_time)
    #         result = xmpp.Iq("result", to=jidFrom)
    #         result.setID(iq.getID())
    #         result.setTag("query", {"seconds": str(uptime)}, xmpp.NS_LAST)
    #         result.setTagData("query", config.IDENTIFIER["name"])
    #         stanza_send(cl, result)
    #     raise xmpp.NodeProcessed()

    #
    # def iqVersionHandler(self, cl, iq):
    #     iType = iq.getType()
    #     jidTo = iq.getTo()
    #     if iType == "get" and jidTo == config.TRANSPORT_ID:
    #         result = iq.buildReply("result")
    #         Query = result.getTag("query")
    #         Query.setTagData("name", config.IDENTIFIER["name"])
    #         os_name = "{0} {2:.16} [{4}]".format(*os.uname())
    #         python_version = "{0} {1}.{2}.{3}".format(sys.subversion[0], *sys.version_info)
    #         # TODO: WTF
    #         Query.setTagData("version", 666)
    #         Query.setTagData("os", "%s / %s" % (os_name, python_version))
    #         stanza_send(cl, result)
    #     raise xmpp.NodeProcessed()

    # def iqStatsHandler(self, cl, iq):
    #     jid_to_str = iq.getTo()
    #     i_type = iq.getType()
    #     iq_children = iq.getQueryChildren()
    #     result = iq.buildReply("result")
    #     if i_type == "get" and jid_to_str == config.TRANSPORT_ID:
    #         querypayload = list()
    #         if not iq_children:
    #             keys = sorted(self.sDict.keys(), reverse=True)
    #             for key in keys:
    #                 Node = xmpp.Node("stat", {"name": key})
    #                 querypayload.append(Node)
    #         else:
    #             users = self.calc_stats()
    #             shell = os.popen("ps -o vsz,rss,%%cpu,time -p %s" % os.getpid()).readlines()
    #             memVirt, memReal, cpuPercent, cpuTime = shell[1].split()
    #             stats = {"users": users, "KB": [memVirt, memReal],
    #                      "percent": [cpuPercent], "seconds": [cpuTime]}
    #             for Child in iq_children:
    #                 if Child.getName() != "stat":
    #                     continue
    #                 name = Child.getAttr("name")
    #                 if name in self.sDict:
    #                     attr = self.sDict[name]
    #                     value = stats[attr].pop(0)
    #                     Node = xmpp.Node("stat", {"units": attr})
    #                     Node.setAttr("name", name)
    #                     Node.setAttr("value", value)
    #                     querypayload.append(Node)
    #         if querypayload:
    #             result.setQueryPayload(querypayload)
    #             stanza_send(cl, result)

    def iq_disco_handler(self, transport, iq_raw):
        logger.debug('handling disco')

        iq = IQ(iq_raw)

        if iq.i_type == "get" and not iq.node and iq.jid_to_str == TRANSPORT_ID:
            query = [Node("identity", IDENTIFIER)]
            result = iq_raw.buildReply("result")
            if iq.ns == NS_DISCO_INFO:
                for key in self.gateway.features:
                    node = Node("feature", {"var": key})
                    query.append(node)
                result.setQueryPayload(query)
            elif iq.ns == NS_DISCO_ITEMS:
                result.setQueryPayload(query)
            stanza_send(transport, str(result))
        raise NodeProcessed()

    @staticmethod
    def iq_gateway_handler(cl, iq):

        jid_to = iq.getTo()
        i_type = iq.getType()
        jid_to_str = jid_to.getStripped()
        iq_children = iq.getQueryChildren()

        if jid_to_str == config.TRANSPORT_ID:
            result = iq.buildReply("result")
            if i_type == "get" and not iq_children:
                query = Node("query", {"xmlns": NS_GATEWAY})
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
                    x_node = library.xmpp.simplexml.Node("prompt")
                    x_node.setData(phone[0])
                    result.setQueryPayload([x_node])
            else:
                raise NodeProcessed()
            stanza_send(cl, result)


    @staticmethod
    def vcard_get_photo(url, encode=True):
        logger.debug('vcard_get_photo')
        try:
            opener = urllib.urlopen(url)
            data = opener.read()
            if data and encode:
                data = data.encode("base64")
            return data
        except IOError:
            logger.debug('IO error while getting photo')
            pass


    def iq_vcard_build(self, tags):
        logger.debug('iq_vcard_build')
        vcard = Node("vCard", {"xmlns": NS_VCARD})
        for key in tags.keys():
            if key == "PHOTO":
                bval = vcard.setTag("PHOTO")
                bval.setTagData("BINVAL", self.vcard_get_photo(tags[key]))
            else:
                vcard.setTagData(key, tags[key])
        return vcard

    def iq_vcard_handler(self, cl, iq):
        logger.debug('iq_vcard_handler')
        jid_from = iq.getFrom()
        jid_to = iq.getTo()
        jid = jid_from.getStripped()
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
            elif database.is_client(jid):
                friends = database.get_friends(jid)
                if friends:
                    friend_jid = get_friend_jid(jid_to_str, jid)
                    json = user_api.get_user_data(jid, friend_jid, ["screen_name", config.PHOTO_SIZE])
                    values = {"NICKNAME": json.get("name", str(json)),
                              "URL": "http://vk.com/id%s" % friend_jid,
                              "DESC": "Contact uses VK4XMPP Transport\n%s" % _DESC}
                    if friend_jid in friends:
                        values["PHOTO"] = json.get(config.PHOTO_SIZE) or config.URL_VCARD_NO_IMAGE
                    vcard = self.iq_vcard_build(values)
                    result.setPayload([vcard])
                else:
                    result = self.iq_build_error(iq, ERR_BAD_REQUEST, "Your friend-list is null.")
            else:
                result = self.iq_build_error(iq, ERR_REGISTRATION_REQUIRED,
                                             "You're not registered for this action.")
        else:
            raise NodeProcessed()
        stanza_send(cl, result)


def get_handler(gateway):
    return IQHandler(gateway).handle