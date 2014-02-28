from __future__ import unicode_literals
from hashlib import sha1
import logging

from lxml import etree

from cystanza.namespaces import NS_COMPONENT_ACCEPT
from cystanza.stanza import Stanza
from xmpp import dispatcher, transports


logger = logging.getLogger("xmpp")


class Component(object):
    def __init__(self, transport, server, port=5222):
        self.namespace = NS_COMPONENT_ACCEPT
        self.default_namespace = self.namespace
        self.disconnect_handlers = []
        self.server = server
        self.port = port
        self.connected = None
        self.connection = None
        self.registered_name = None
        self.dispatcher = None
        self.domains = [server, ]
        self.handshake = False
        self.transport = transport

    def event(self, name, args=None):
        raise NotImplementedError('event handler not overridden')

    def is_connected(self):
        return self.connected

    def connect(self, host, port):
        self.connection = transports.TCPSocket()
        connected = self.connection.connect(host, port)
        if not connected:
            return None
        self.connected = True
        self.dispatcher = dispatcher.Dispatcher(self.connection, self)
        self.dispatcher.init()

        while not self.dispatcher.builder.attributes:
            if not self.process(5):
                return None

        return self.connected

    def process(self, timeout=8):
        return self.dispatcher.process(timeout)

    def auth(self, user, password):
        return self.auth_component(user, password)

    def auth_component(self, user, password):
        logger.debug('authenticating component')
        handshake_hash = sha1(self.dispatcher.builder.attributes['id'] + password)
        self.dispatcher.set_handshake_handler(self.handshake_handler)
        q = etree.Element('handshake', xmlns=NS_COMPONENT_ACCEPT)
        q.text = handshake_hash.hexdigest()
        self.connection.send(etree.tostring(q))
        while not self.handshake:
            self.process(1)
        logger.debug('authenticated')
        self.registered_name = user
        return self.handshake

    def register_handler(self, *args, **kwargs):
        self.dispatcher.register_handler(*args, **kwargs)

    def handshake_handler(self):
        self.handshake = True

    def send(self, stanza):
        if isinstance(stanza, Stanza):
            return self.dispatcher.send(stanza)
        return self.dispatcher.send(stanza)