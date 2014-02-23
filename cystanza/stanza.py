# coding=utf-8
from __future__ import unicode_literals
from lxml.etree import tostring
from lxml import etree
from namespaces import NS_NICK


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
        self.stanza_id = stanza_id
        self.base = None
        # self.build()

    def build(self):
        attributes = {}
        update_if_exist(attributes, self.origin, 'from')
        update_if_exist(attributes, self.destination, 'to')
        update_if_exist(attributes, self.stanza_type, 'type')
        update_if_exist(attributes, self.namespace, 'xmlns')
        update_if_exist(attributes, self.stanza_id, 'id')
        base_element = etree.Element(self.element_name, attributes)
        self.base = base_element

    def __str__(self):
        self.build()
        return tostring(self.base, encoding='utf-8')


class Message(Stanza):
    """
    Message to or from transport with "from" attribute required
    """
    def __init__(self, origin, destination, message_type, message_id=None):
        if message_type not in ['normal', 'chat', 'groupchat', 'headline', 'error']:
            raise ValueError('unknown message type %s' % message_type)
        self.message_type = message_type
        self.message_id = message_id
        super(Message, self).__init__('message', origin, destination, message_type)


class ChatMessage(Message):
    def __init__(self, origin, destination, text, subject=None, message_type='chat'):
        self.text = text
        self.subject = subject
        super(ChatMessage, self).__init__(origin, destination, message_type)

    def build(self):
        super(ChatMessage, self).build()
        body = etree.SubElement(self.base, 'body')
        body.text = self.text

        if self.subject:
            subject = etree.SubElement(self.base, 'subject')
            subject.text = self.subject


class Presence(Stanza):
    """
    Network availability message of entity
    """
    def __init__(self, origin, destination, status=None, show=None, nickname=None):
        self.status = status
        self.show = show
        self.nickname = nickname
        super(Presence, self).__init__('presence', origin, destination)

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


class InfoQuery(Stanza):
    def __init__(self, origin, destination, iq_type):
        if iq_type not in ['get', 'set', 'result', 'error']:
            raise ValueError('unknown iq type %s' % iq_type)
        super(InfoQuery, self).__init__('iq', origin, destination, iq_type)
        self.iq_type = iq_type

if __name__ == '__main__':
    s = Stanza('iq', 'vk.cydev', stanza_type='hallo')
    m = Message('cyvk@vk.cydev', 'ernado@vk.cydev', 'chat')
    p = Presence('vk.s1.cydev', 'ernado@vk.cydev', 'down the', nickname='Test')
    # b = p.base
    # b.append(s.base)
    t = ChatMessage('ernado@vk.s1.cydev', 'vk.s1.cydev', 'hello, азаз', subject='приветствие')
    print(t)