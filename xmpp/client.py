from __future__ import unicode_literals
from hashlib import sha1
import logging

from cystanza.namespaces import NS_COMPONENT_ACCEPT
from cystanza.stanza import Stanza, Handshake
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
        logger.debug('client: starting connection')
        self.connection = transports.TCPSocket()
        connected = self.connection.connect(host, port)
        logger.debug('client: connected: %s' % connected)
        if not connected:
            return None
        self.connected = True
        self.dispatcher = dispatcher.Dispatcher(self.connection, self)
        self.dispatcher.init()
        logger.debug('dispatcher inited')

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
        handshake_hash = sha1(self.dispatcher.builder.attributes['id'] + password).hexdigest()
        self.dispatcher.set_handshake_handler(self.handshake_handler)
        self.connection.send(Handshake(handshake_hash, NS_COMPONENT_ACCEPT))
        logger.debug('waiting on handshake')
        self.process(5)
        if self.handshake:
            logger.debug('authenticated')
        self.registered_name = user
        return self.handshake

    def register_handler(self, *args, **kwargs):
        self.dispatcher.register_handler(*args, **kwargs)

    def handshake_handler(self):
        logger.debug('handshake handler')
        self.handshake = True

    def send(self, stanza):
        return self.dispatcher.send(stanza)