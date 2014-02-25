from __future__ import unicode_literals
import logging

from lxml import etree

from cystanza.namespaces import NS_COMPONENT_ACCEPT, NS_STREAMS
from cystanza.fabric import get_stanza
from cystanza.builder import Builder
from cystanza.stanza import Stanza, Presence, FeatureQuery, Handshake, ChatMessage
from cystanza.forms import RegistrationRequest, RegistrationFormStanza
from handlers import message_handler, presence_handler
from handlers import registration_form_handler, registration_request_handler, discovery_request_handler


logger = logging.getLogger("xmpp")


class Dispatcher():
    def __init__(self, connection, client):
        self.handshake_handler = None
        self.namespace = NS_COMPONENT_ACCEPT
        self.connection = None
        self.client = client
        self.connection = connection
        self.parser = etree.XMLPullParser(events=('start', 'end'))
        self.builder = Builder(self.test_dispatch)

    def set_handshake_handler(self, handler):
        self.handshake_handler = handler

    def init(self):
        logger.debug('dispatcher init')
        ns = self.namespace
        init_str = '<?xml version="1.0"?><stream:stream xmlns="%s" version="1.0" xmlns:stream="%s">' % (ns, NS_STREAMS)
        self.connection.send(init_str)

    def test_dispatch(self, stanza):
        s = get_stanza(stanza)
        if isinstance(s, ChatMessage):
            return message_handler(s)
        if isinstance(s, Presence):
            return presence_handler(s)
        if isinstance(s, RegistrationRequest):
            return registration_request_handler(s)
        if isinstance(s, RegistrationFormStanza):
            return registration_form_handler(s)
        if isinstance(s, FeatureQuery):
            return discovery_request_handler(s)
        if isinstance(s, Handshake):
            return self.handle_handshake()

    def process(self, timeout=8):
        logger.error('dispatcher process')
        if self.connection.pending_data(timeout):
            try:
                data = self.connection.receive()
            except IOError as e:
                logger.error('IO error while reading from socket: %s' % e)
                return None
            try:
                self.builder.parse(data)
            except etree.Error as e:
                logger.error('builder error: ' % e)
            if data:
                return len(data)
        logger.error('no data')
        return True

    def send(self, stanza):
        if isinstance(stanza, Stanza):
            stanza.namespace = self.namespace
            self.connection.send(stanza)

    def disconnect(self):
        self.connection.send('</stream:stream>')
        while self.process(1):
            pass

    def handle_handshake(self):
        if self.handshake_handler:
            self.handshake_handler()
