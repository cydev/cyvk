# coding=utf-8
from __future__ import unicode_literals
from lxml.etree import tostring
from lxml import etree
from namespaces import NS_NICK, NS_DELAY
import uuid

STANZA_MESSAGE = 'message'
STANZA_IQ = 'iq'
STANZA_PRESENCE = 'presence'
STANZA_PROBE = 'probe'


def update_if_exist(d, val, name):
    if val:
        d.update({name: val})


class Stanza(object):
    """
    XMPP communication primitive
    """

    def __init__(self, element_type, origin=None, destination=None, stanza_type=None, namespace=None, stanza_id=None):
        self.element_name = element_type
        self.origin = origin
        self.destination = destination
        self.stanza_type = stanza_type
        self.namespace = namespace
        self.stanza_id = stanza_id or str(uuid.uuid1())
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


class Message(Stanza):
    """
    Message to or from transport with "from" attribute required
    """

    def __init__(self, origin, destination, message_type, message_id=None, timestamp=None):
        if message_type not in ['normal', 'chat', 'groupchat', 'headline', 'error']:
            raise ValueError('unknown message type %s' % message_type)
        self.message_type = message_type
        self.message_id = message_id
        self.timestamp = timestamp
        super(Message, self).__init__(STANZA_MESSAGE, origin, destination, message_type)

    def build(self):
        super(Message, self).build()
        etree.SubElement(self.base, 'x', stamp=self.timestamp, xmlns=NS_DELAY)


class ChatMessage(Message):
    def __init__(self, origin, destination, text, subject=None, message_type='chat', timestamp=None):
        self.text = text
        self.subject = subject
        super(ChatMessage, self).__init__(origin, destination, message_type, timestamp=timestamp)

    def build(self):
        super(ChatMessage, self).build()
        body = etree.SubElement(self.base, 'body')
        body.text = self.text

        if self.subject:
            subject = etree.SubElement(self.base, 'subject')
            subject.text = self.subject

        return self.base


class Answer(Message):
    def __init__(self, origin, destination, message_type='chat', message_id=None):
        super(Answer, self).__init__(origin, destination, message_type=message_type, message_id=message_id)

    def build(self):
        super(Answer, self).build()
        etree.SubElement(self.base, 'received', xmlns='urn:xmpp:receipts')


class Presence(Stanza):
    """
    Network availability message of entity
    """

    def __init__(self, origin, destination, status=None, show=None, nickname=None, presence_type=None):
        self.status = status
        self.show = show
        self.nickname = nickname
        super(Presence, self).__init__(STANZA_PRESENCE, origin, destination, stanza_type=presence_type)

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
    def __init__(self, origin, destination, iq_type):
        if iq_type not in ['get', 'set', 'result', 'error']:
            raise ValueError('unknown iq type %s' % iq_type)
        super(InfoQuery, self).__init__(STANZA_IQ, origin, destination, iq_type)
        self.iq_type = iq_type


if __name__ == '__main__':
    p = Probe('s1.cydev.ru', 'ernado@vk.cydev')
    print(p.stanza_type)
    print(p)