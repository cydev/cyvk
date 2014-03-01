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
from user import UserApi

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
        self.transport = client.transport

    def set_handshake_handler(self, handler):
        self.handshake_handler = handler

    def init(self):
        logger.debug('dispatcher init')
        ns = self.namespace
        init_str = '<?xml version="1.0"?><stream:stream xmlns="%s" version="1.0" xmlns:stream="%s">' % (ns, NS_STREAMS)
        self.connection.send(init_str)

    def test_dispatch(self, stanza):
        logger.debug('dispatching %s' % str(stanza))
        s = get_stanza(stanza)
        logger.debug('dispatched: %s' % s)

        if not s:
            return logger.debug('dispatcher: no stanza')
        jid = s.get_origin()

        if isinstance(s, Handshake):
            return self.handle_handshake()

        if jid is None:
            return logger.debug('dispatcher: no jid')

        if jid not in self.transport.users:
            user = UserApi(self.transport, jid)
        else:
            user = self.transport.users[jid]

        logger.debug('dispatching on type of stanza')
        if isinstance(s, ChatMessage):
            return message_handler(user, s)
        if isinstance(s, Presence):
            return presence_handler(user, s)
        if isinstance(s, RegistrationRequest):
            logger.debug('dispatched registration request')
            return registration_request_handler(user, s)
        if isinstance(s, RegistrationFormStanza):
            return registration_form_handler(user, s)
        if isinstance(s, FeatureQuery):
            logger.debug('dispatched discovery request')
            return discovery_request_handler(user, s)

    def process(self, timeout=3):
        logger.debug('dispatcher iteration started')
        if self.connection.pending_data(timeout):
            logger.debug('dispatcher: some data')
            try:
                logger.debug('dispatcher: receiving')
                data = self.connection.receive()
            except IOError as e:
                logger.error('IO error while reading from socket: %s' % e)
                return None
            try:
                logger.debug('dispatcher: parsing')
                self.builder.parse(data)
            except etree.Error as e:
                logger.error('builder error: ' % e)
            if data:
                return len(data)
        else:
            logger.debug('no data')
        logger.debug('dispatcher iteration ended with no data')
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
