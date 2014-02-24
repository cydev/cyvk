# coding: utf-8
from __future__ import unicode_literals, absolute_import

import logging

from config import IDENTIFIER, TRANSPORT_ID
from handlers.iq import _send_form
from parallel.stanzas import push
from features import TRANSPORT_FEATURES
from parallel import realtime
import config
from transport.stanzas import generate_error
import user as user_api
from xmpp.exceptions import NodeProcessed
from xmpp.stanza import (NS_REGISTER,
                         NS_DISCO_ITEMS, NS_DISCO_INFO, ERR_BAD_REQUEST, Node)
from errors import AuthenticationException
import database


logger = logging.getLogger("cyvk")


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


def _process_form(iq, jid):
    logger.debug('received register form from %s' % jid)

    assert isinstance(jid, unicode)

    result = iq.buildReply("result")

    query = iq.getTag("query")

    try:
        token = query.getTag("x").getTag("field", {"var": "password"}).getTagData("value")
    except AttributeError:
        raise AuthenticationException('no password')

    try:
        token = token.split("#access_token=")[1].split("&")[0].strip()
    except (IndexError, AttributeError):
        logger.debug('access token is probably in raw format')

    logger.debug('form processed')

    user_attributes = database.get_description(jid)

    logger.debug('got description %s' % user_attributes)
    if not user_attributes:
        logger.debug('user %s is not in database' % jid)
    else:
        raise NotImplementedError('already in database')

    try:
        if not token:
            raise AuthenticationException('no token')
        user_api.connect(jid, token)
        realtime.set_token(jid, token)
        user_api.initialize(jid)
    except AuthenticationException:
        logger.error('user %s connection failed (from iq)' % jid)
        return generate_error(iq, ERR_BAD_REQUEST, 'Incorrect password or access token')

    realtime.set_last_activity_now(jid)
    user_api.add_client(jid)
    database.insert_user(jid, None, token, None, False)
    logger.debug('registration for %s completed' % jid)

    return result


def handler(_, stanza):
    ns = stanza.getQueryNS()

    mapping = {
        NS_REGISTER: iq_register_handler,
        NS_DISCO_INFO: iq_disco_handler,
        NS_DISCO_ITEMS: iq_disco_handler
    }

    try:
        mapping[ns](stanza)
    except KeyError:
        logger.critical('passing key %s' % ns)

    raise NodeProcessed()


def iq_register_handler(stanza):
    jid = unicode(stanza.getFrom().getStripped())
    logger.debug('register handler for %s' % jid)

    destination_jid = stanza.getTo().getStripped()

    if destination_jid != config.TRANSPORT_ID:
        logger.debug('register not to transport')
        return

    try:
        h = {'get': _send_form, 'set': _process_form}[stanza.getType()]
        push(h(stanza, jid))
    except (NotImplementedError, KeyError) as e:
        logger.debug('requested feature not implemented: %s' % e)
        push(generate_error(stanza, 0, "Requested feature not implemented: %s" % e))


def iq_disco_handler(iq_raw):
    logger.debug('handling disco')

    iq = IQ(iq_raw)

    if iq.i_type == "get" and not iq.node and iq.jid_to_str == TRANSPORT_ID:
        query = [Node("identity", IDENTIFIER)]
        result = iq_raw.buildReply("result")
        if iq.ns == NS_DISCO_INFO:
            for key in TRANSPORT_FEATURES:
                node = Node("feature", {"var": key})
                query.append(node)
            result.setQueryPayload(query)
        elif iq.ns == NS_DISCO_ITEMS:
            result.setQueryPayload(query)
        push(result)

