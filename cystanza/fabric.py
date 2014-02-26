from __future__ import unicode_literals
import logging

from lxml import etree

from cystanza.stanza import STANZA_MESSAGE, STANZA_PRESENCE, Presence, STANZA_IQ, ChatMessage, FeatureQuery, Handshake
from cystanza.namespaces import NS_RECEIPTS, NS_DISCO_INFO, NS_DISCO_ITEMS, NS_REGISTER
from cystanza.forms import FORM_TOKEN_VAR, RegistrationFormStanza, RegistrationRequest


logger = logging.getLogger("xmpp")


def get(attrs, name):
    if name in attrs:
        return unicode(attrs[name])
    else:
        return None


def get_stanza(root):
    logger.debug('got stanza: %s' % etree.tostring(root))
    stanza_name = root.xpath('local-name()')
    a = root.attrib

    if stanza_name == 'handshake':
        return Handshake()

    origin = get(a, 'from')
    destination = get(a, 'to')
    stanza_type = get(a, 'type')
    stanza_id = get(a, 'id')
    ns = get(a, 'xmlns')

    if stanza_name == STANZA_PRESENCE:
        status = root.findtext('{*}status')
        return Presence(origin, destination, status, presence_type=stanza_type, namespace=ns)

    if stanza_name == STANZA_MESSAGE:
        text = root.findtext('{*}body')
        requests_answer = root.find('{%s}request' % NS_RECEIPTS) is not None

        if text:
            text = unicode(text)
            return ChatMessage(origin, destination, text, ns, requests_answer)

        composing = root.find('{*}composing')
        if composing is not None:
            logger.warning('composing not implemented')

    if stanza_name == STANZA_IQ:
        query = root.find('.//{*}query')
        query_namespace = None

        if query is not None:
            query_raw = unicode(etree.tostring(query))
            start_attribute = 'xmlns="'
            start = query_raw.find(start_attribute) + len(start_attribute)
            query_namespace = query_raw[start:query_raw.find('"', start)]

        if (query_namespace == NS_DISCO_INFO or query_namespace == NS_DISCO_ITEMS) and stanza_type == 'get':
            return FeatureQuery(origin, destination, stanza_id, namespace=ns, query_namespace=query_namespace)

        if query_namespace == NS_REGISTER and stanza_type == 'get':
            return RegistrationRequest(origin, destination, stanza_id, ns)

        token = root.findtext('.//{*}field[@var="%s"]/{*}value' % FORM_TOKEN_VAR)
        if token:
            return RegistrationFormStanza(origin, destination, unicode(token), stanza_id, stanza_type)