__author__ = 'ernado'
import logging

import library.vkapi as api
import library.xmpp as xmpp
from messaging import msg_send
from config import TRANSPORT_ID

logger = logging.getLogger("vk4xmpp")

def captcha_accept(gateway, cl, args, jid_to, jid_from_str):
        logger.debug('captcha accept from %s' % jid_from_str)

        if not args:
            return

        # GLOBAL LIST USAGE
        # CLIENT
        client = gateway.clients[jid_from_str]

        if client.vk.engine.captcha:
            logger.debug("user %s called captcha challenge" % jid_from_str)
            client.vk.engine.captcha["key"] = args
            retry = False
            try:
                logger.debug("retrying for user %s" % jid_from_str)
                retry = client.vk.engine.retry()
            except api.CaptchaNeeded:
                logger.error("retry for user %s failed!" % jid_from_str)
                client.vk.captcha_challenge()
            if retry:
                logger.debug("retry for user %s OK" % jid_from_str)
                answer = "Captcha valid."
                presence = xmpp.protocol.Presence(jid_from_str, frm=TRANSPORT_ID)
                presence.setStatus("") # is it needed?
                presence.setShow("available")
                gateway.send(presence)
                client.try_again()
            else:
                answer = "Captcha invalid."
        else:
            answer = "Not now. Ok?"
        if answer:
            msg_send(cl, jid_from_str, answer, jid_to)