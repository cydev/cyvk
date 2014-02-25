# coding=utf-8
from __future__ import unicode_literals
from lxml.etree import tostring
from lxml import etree
from namespaces import NS_NICK, NS_DELAY, NS_RECEIPTS, NS_DISCO_INFO, NS_DISCO_ITEMS
from cystanza.errors import ERR_FEATURE_NOT_IMPLEMENTED, ERR_BAD_REQUEST
from cystanza.namespaces import NS_STANZAS
import uuid

STANZA_MESSAGE = 'message'
STANZA_IQ = 'iq'
STANZA_PRESENCE = 'presence'
STANZA_PROBE = 'probe'
STANZA_ERROR = 'error'
STANZA_HANDSHAKE = 'handshake'


# TODO: Make getters/setters?
def update_if_exist(d, val, name):
    if val:
        d.update({name: val})


def assert_unicode(val):
    if val is not None and not isinstance(val, unicode):
        raise ValueError('%s (%s) is not unicode' % (val, type(val)))


class Stanza(object):
    """
    XMPP communication primitive
    """

    def __init__(self, element_type, origin=None, destination=None, stanza_type=None, namespace=None, stanza_id=None):
        assert_unicode(element_type)
        assert_unicode(origin)
        assert_unicode(destination)
        assert_unicode(stanza_type)
        assert_unicode(namespace)
        assert_unicode(stanza_id)
        self.element_name = element_type
        self.origin = origin
        self.destination = destination
        self.stanza_type = stanza_type
        self.namespace = namespace
        self.stanza_id = stanza_id or unicode(uuid.uuid1())
        self.base = None

    def build(self):
        attributes = {}
        update_if_exist(attributes, self.origin, 'from')
        update_if_exist(attributes, self.destination, 'to')
        update_if_exist(attributes, self.stanza_type, 'type')
        update_if_exist(attributes, self.namespace, 'xmlns')
        update_if_exist(attributes, self.stanza_id, 'id')

        base_element = etree.Element(self.element_name, attributes)
        self.base = base_element
        return self.base

    def __str__(self):
        self.build()
        return tostring(self.base, encoding='utf-8')

    @staticmethod
    def get_stripped(jid):
        if jid is None:
            return None
        if jid.find('/'):
            return jid.split('/')[0]

    def get_origin(self):
        return self.get_stripped(self.origin)

    def get_destination(self):
        return self.get_stripped(self.destination)


class Handshake(Stanza):
    def __init__(self):
        super(Handshake, self).__init__(STANZA_HANDSHAKE)


class Message(Stanza):
    """Message to or from transport with "from" attribute required"""

    def __init__(self, origin, destination, message_type, message_id=None, timestamp=None, namespace=None):
        if message_type not in ['normal', 'chat', 'groupchat', 'headline', 'error']:
            raise ValueError('unknown message type %s' % message_type)
        self.message_type = message_type
        self.message_id = message_id
        self.timestamp = timestamp
        super(Message, self).__init__(STANZA_MESSAGE, origin, destination, message_type, namespace=namespace)

    def build(self):
        super(Message, self).build()

        attrs = {'xmlns': NS_DELAY}
        if self.timestamp:
            attrs.update({'stamp': self.timestamp})
        etree.SubElement(self.base, 'x', attrs)

        return self.base


class ChatMessage(Message):
    def __init__(self, origin, destination, text, namespace=None, requests_answer=False,
                 message_type='chat', timestamp=None, subject=None):
        self.text = text
        self.subject = subject
        self.requests_answer = requests_answer
        super(ChatMessage, self).__init__(origin, destination, message_type, timestamp=timestamp, namespace=namespace)

    def build(self):
        super(ChatMessage, self).build()
        body = etree.SubElement(self.base, 'body')
        body.text = self.text

        if self.subject:
            subject = etree.SubElement(self.base, 'subject')
            subject.text = self.subject

        if self.requests_answer:
            etree.SubElement(self.base, 'request', xmlns=NS_RECEIPTS)

        return self.base


class Answer(Message):
    def __init__(self, origin, destination, message_type='chat', message_id=None, namespace=None):
        super(Answer, self).__init__(origin, destination, message_type=message_type, message_id=message_id,
                                     namespace=namespace)

    def build(self):
        super(Answer, self).build()
        etree.SubElement(self.base, 'received', xmlns='urn:xmpp:receipts')


class Presence(Stanza):
    """Network availability message of entity"""

    def __init__(self, origin, destination, status=None, show=None, nickname=None, presence_type=None, namespace=None):
        self.status = status
        self.show = show
        self.nickname = nickname
        super(Presence, self).__init__(STANZA_PRESENCE, origin, destination, stanza_type=presence_type,
                                       namespace=namespace)

    def build(self):
        super(Presence, self).build()

        if self.nickname:
            show = etree.SubElement(self.base, 'nick', xmlns=NS_NICK)
            show.text = self.nickname

        if self.show:
            show = etree.SubElement(self.base, 'show')
            show.text = self.show

        if self.status:
            status = etree.SubElement(self.base, 'status')
            status.text = self.status

        return self.base


class Probe(Presence):
    def __init__(self, origin, destination):
        super(Probe, self).__init__(origin, destination, presence_type=STANZA_PROBE)


class InfoQuery(Stanza):
    def __init__(self, origin, destination, query_type, query_id=None, namespace=None):
        if query_type not in ['get', 'set', 'result', 'error']:
            raise ValueError('unknown iq type %s' % query_type)
        self.query_type = query_type
        super(InfoQuery, self).__init__(STANZA_IQ, origin, destination, namespace=namespace,
                                        stanza_type=query_type, stanza_id=query_id)


class FeatureQuery(InfoQuery):
    """Stanza for quering features"""

    def __init__(self, origin, destination, query_id, identity=None, features=None, namespace=None,
                 query_namespace=None):
        self.identity = identity
        namespace = namespace or NS_DISCO_ITEMS
        self.features = features or []
        self.query_ns = query_namespace or NS_DISCO_INFO
        super(FeatureQuery, self).__init__(origin, destination, 'result', query_id, namespace=namespace)

    def build(self):
        super(FeatureQuery, self).build()
        q = etree.SubElement(self.base, 'query', xmlns=self.query_ns)
        if self.identity:
            etree.SubElement(q, 'identity', {'category': 'gateway', 'type': 'vk', 'name': self.identity})
        if self.query_ns:
            for feature in self.features:
                etree.SubElement(q, 'feature', var=feature)
        return self.base


class ErrorStanza(Stanza):
    def __init__(self, stanza, error_name, error_ns, text=None, namespace=None):
        """
        :type stanza: Stanza
        """
        self.text = text
        self.error_name = error_name
        self.error_ns = error_ns
        super(ErrorStanza, self).__init__(stanza.element_name, stanza.destination, stanza.origin, namespace=namespace,
                                          stanza_type=STANZA_ERROR, stanza_id=stanza.stanza_id)

    def build(self):
        super(ErrorStanza, self).build()
        error_base = etree.SubElement(self.base, 'error')
        attributes = {}
        update_if_exist(attributes, self.error_ns, 'xmlns')
        error_element = etree.SubElement(error_base, self.error_name, attributes)
        if self.text:
            error_element.text = self.text
        return self.base


class NotImplementedErrorStanza(ErrorStanza):
    def __init__(self, stanza, text=None, namespace=None):
        ns = NS_STANZAS
        super(NotImplementedErrorStanza, self).__init__(stanza, ERR_FEATURE_NOT_IMPLEMENTED, ns, text, namespace)


class BadRequestErrorStanza(ErrorStanza):
    def __init__(self, stanza, text=None, namespace=None):
        super(BadRequestErrorStanza, self).__init__(stanza, ERR_BAD_REQUEST, NS_STANZAS, text, namespace)


if __name__ == '__main__':
    s = "<iq from='ernado@s1.cydev/7888950191393122917632183' to='vk.s1.cydev' type='set' id='purplee266aec6'><query xmlns='jabber:iq:register'><x xmlns='jabber:x:data' type='submit'><field var='link'><value>https://oauth.vk.com/authorize?client_id=4157729&amp;scope=69634&amp;redirect_uri=http://oauth.vk.com/blank.html&amp;display=page&amp;response_type=token</value></field><field var='password'><value>https://oauth.vk.com/blank.html#access_token=fb0cff246416544c3aaef1f1e389fe657d627d0fbbed9652f869dc7ea1d275085d2fe47133e1d99261262&amp;expires_in=0&amp;user_id=224196364</value></field></x></query></iq>"
    e = etree.fromstring(s)
    password_field = e.findtext('.//{*}field[@var="password"]/{*}value')
    if password_field is not None:
        print(password_field)
        # <iq xmlns="jabber:component:accept" to="ernado@s1.cydev/7888950191393122917632183" from="vk.s1.cydev" id="purpledisco9bf061e" type="result"><query xmlns="http://jabber.org/protocol/disco#info"><identity category="gateway" type="vk" name="cyvk transport" /><feature var="http://jabber.org/protocol/disco#items" /><feature var="http://jabber.org/protocol/disco#info" /><feature var="urn:xmpp:receipts" /><feature var="jabber:iq:register" /><feature var="jabber:x:delay" /><feature var="jabber:iq:last" /></query></iq>
        # <iq from="vk.s1.cydev" id="purpledisco9bf063e" to="ernado@s1.cydev" type="result" xmlns="jabber:component:accept"><query xmlns="http://jabber.org/protocol/disco#info">                          <identity category="gateway" name="cyvk transport" type="vk"/><feature var="http://jabber.org/protocol/disco#items"/><feature var="http://jabber.org/protocol/disco#info"/><feature var="urn:xmpp:receipts"/><feature var="jabber:iq:register"/><feature var="jabber:x:delay"/><feature var="jabber:iq:last"/></query></iq>
        # print(e.findtext('.//{*}field[@var="password"]'))
        # print(FeatureQuery('s1.cydev.ru', 'ernado@vk.cydev', unicode(uuid.uuid1()), 'vk.s1.cydev', ['keks', 'pels']))