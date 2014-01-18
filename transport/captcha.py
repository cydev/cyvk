__author__ = 'ernado'
import logging

# import library.vkapi as api

logger = logging.getLogger("cyvk")

def captcha_accept(args, jid_to, jid_from_str):

    raise NotImplementedError('captcha')

    # logger.debug('captcha accept from %s' % jid_from_str)
    #
    # if not args:
    #     return
    #
    # # GLOBAL LIST USAGE
    # # CLIENT
    # client = gateway.clients[jid_from_str]
    #
    # if client.vk.engine.captcha:
    #     logger.debug("user %s called captcha challenge" % jid_from_str)
    #     client.vk.engine.captcha["key"] = args
    #     retry = False
    #     try:
    #         logger.debug("retrying for user %s" % jid_from_str)
    #         retry = client.vk.engine.retry()
    #     except CaptchaNeeded:
    #         logger.error("retry for user %s failed!" % jid_from_str)
    #         client.vk.captcha_challenge()
    #     if retry:
    #         logger.debug("retry for user %s OK" % jid_from_str)
    #         answer = "Captcha valid."
    #         presence = xmpp.protocol.Presence(jid_from_str, frm=TRANSPORT_ID)
    #         presence.setStatus("") # is it needed?
    #         presence.setShow("available")
    #         database.queue_stanza(presence)
    #
    #         client.try_again()
    #     else:
    #         answer = "Captcha invalid."
    # else:
    #     answer = "Not now. Ok?"
    # if answer:
    #     send_message(cl, jid_from_str, answer, jid_to)

def captcha_challenge(gateway, jid):
    raise NotImplementedError('Captcha')
    # if self.engine.captcha:
    #     logger.debug("VKLogin: sending message with captcha to %s" % jid)
    #     body = "WARNING: VK sent captcha to you."
    #              " Please, go to %s and enter text from image to chat."
    #              " Example: !captcha my_captcha_key. Tnx" % self.engine.captcha["img"]
    #     captcha_message = xmpp.Message(self.jid_from, body, "chat", frm=TRANSPORT_ID)
    #     x_tag = captcha_message.setTag("x", {}, xmpp.NS_OOB)
    #     x_tag.setTagData("url", self.engine.captcha["img"])
    #     c_tag = captcha_message.setTag("captcha", {}, xmpp.NS_CAPTCHA)
    #     img = vcard_get_photo(self.engine.captcha["img"], False)
    #     if img:
    #         img_hash = sha1(img).hexdigest()
    #         img_encoded = img.encode("base64")
    #         form = xmpp.DataForm("form")
    #         form.setField("FORM_TYPE", xmpp.NS_CAPTCHA, "hidden")
    #         form.setField("from", TRANSPORT_ID, "hidden")
    #         field = form.setField("ocr")
    #         field.setLabel(_("Enter shown text"))
    #         field.delAttr("type")
    #         field.setPayload([xmpp.Node("required"),
    #                           xmpp.Node("media", {"xmlns": xmpp.NS_MEDIA},
    #                                     [xmpp.Node("uri", {"type": "image/jpg"},
    #                                                ["cid:sha1+%s@bob.xmpp.org" % img_hash])])])
    #         c_tag.addChild(node=form)
    #         ob_tag = captcha_message.setTag("data",
    #                                        {"cid": "sha1+%s@bob.xmpp.org" % img_hash, "type": "image/jpg",
    #                                         "max-age": "0"},
    #                                        xmpp.NS_URN_OOB)
    #         ob_tag.setData(img_encoded)
    #     else:
    #         logger.critical("VKLogin: can't add captcha image to message url:%s" % self.engine.captcha["img"])
    #     gateway.send(captcha_message)
    #     presence = xmpp.protocol.Presence(jid, frm=TRANSPORT_ID)
    #     presence.setStatus(body)
    #     presence.setShow("xa")
    #     gateway.send(presence)
    # else:
    #     logger.error("VKLogin: captchaChallenge called without captcha for user %s" % jid)