from __future__ import unicode_literals
from cystanza.stanza import STANZA_MESSAGE, STANZA_PRESENCE, Presence, STANZA_IQ, ChatMessage
from cystanza.namespaces import NS_RECEIPTS
import logging

logger = logging.getLogger("xmpp")


def get(attrs, name):
    if name in attrs:
        return unicode(attrs[name])
    else:
        return None


def remove_resource(jid):
    if jid is None:
        return None
    if jid.find('/'):
        return jid.split('/')[0]


def get_stanza(root):
    stanza_name = root.xpath('local-name()')
    a = root.attrib

    if stanza_name == 'handshake':
        logger.error('handshake got')

    origin = remove_resource(get(a, 'from'))
    destination = remove_resource(get(a, 'to'))
    stanza_type = get(a, 'type')

    if stanza_name == STANZA_PRESENCE:
        logger.error('got presence')
        status = root.findtext('{*}status')
        return Presence(origin, destination, status=status, presence_type=stanza_type)

    if stanza_name == STANZA_MESSAGE:
        # logger.error('got message: %s' % etree.tostring(root, encoding='utf-8'))
        logger.error('got message')
        text = root.findtext('{*}body')
        requests_answer = root.find('{%s}request' % NS_RECEIPTS) is not None

        if text:
            text = unicode(text)
            logger.error('got text: %s' % text)

            return ChatMessage(origin, destination, text, message_type=stanza_type, requests_answer=requests_answer)

        # return ChatMessage object
        composing = root.find('{*}composing')
        if composing is not None:
            logger.error('got composing')

    if stanza_name == STANZA_IQ:
        logger.error('got iq')

        query = root.find('{*}query')

        if query is not None:
            logger.error('iq with query')

            # logger.error('dispatched: %s' % root.xpath('local-name()'))