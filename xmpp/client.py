from __future__ import unicode_literals
from hashlib import sha1
from cystanza.namespaces import NS_COMPONENT_ACCEPT
from cystanza.stanza import Stanza
from stanza import Node
from xmpp import dispatcher, transports
import logging

logger = logging.getLogger("xmpp")


class Component(object):
    def __init__(self, server, port=5222):
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

    def register_disconnect_handler(self, handler):
        # Register handler that will be called on disconnect.
        self.disconnect_handlers.append(handler)

    def disconnected(self):
        # Called on disconnection. Calls disconnect handlers
        self.connected = None
        logger.warning('disconnect detected')
        for handler in self.disconnect_handlers:
            handler()

    def event(self, name, args=None):
        raise NotImplementedError('event handler not overridden')

    def is_connected(self):
        return self.connected

    def connect(self, server=None):
        # Make a tcp/ip connection and start XMPP stream.
        if not server:
            server = (self.server, self.port)
        self.connection = transports.TCPSocket(server)
        connected = self.connection.connect(server)
        if not connected:
            return None
        self.server = server
        self.connected = True
        self.dispatcher = dispatcher.Dispatcher(self.connection, self)
        # self.dispatcher.attach(self)
        self.dispatcher.init()

        while not self.dispatcher.stream.document_attrs:
            if not self.process(5):
                return None
        document_attrs = self.dispatcher.stream.document_attrs
        if 'version' in document_attrs and document_attrs['version'] == "1.0":
            while not self.dispatcher.stream.features and self.process(1):
                pass
        return self.connected

    def process(self, timeout=8):
        return self.dispatcher.process(timeout)

    def auth(self, user, password):
        return self.auth_component(user, password)

    def auth_component(self, user, password):
        logger.debug('authenticating component')
        handshake_hash = sha1(self.dispatcher.stream.document_attrs['id'] + password)
        self.dispatcher.register_handler('handshake', self.handshake_handler, xml_ns=NS_COMPONENT_ACCEPT)
        self.connection.send(Node(NS_COMPONENT_ACCEPT + ' handshake', payload=[handshake_hash.hexdigest()]))
        while not self.handshake:
            self.process(1)
        self.registered_name = user
        return self.handshake

    def handshake_handler(self, _, stanza):
        self.handshake = stanza.getName() == "handshake"

    def register_handler(self, *args, **kwargs):
        self.dispatcher.register_handler(*args, **kwargs)

    def send(self, stanza):
        if isinstance(stanza, Stanza):
            return self.dispatcher.test_send(stanza)
        return self.dispatcher.send(stanza)