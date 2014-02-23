from xmpp import auth, dispatcher, transports
import logging
logger = logging.getLogger("xmpp")


class Component(object):
    def __init__(self, server, port=5222):
        self.namespace = dispatcher.NS_COMPONENT_ACCEPT
        self.default_namespace = self.namespace
        self.disconnect_handlers = []
        self.server = server
        self.port = port
        self.owner = self
        self.connected = None
        self.connection = None
        self.registered_name = None
        self.dispatcher = dispatcher.Dispatcher()
        self.domains = [server, ]

    def register_disconnect_handler(self, handler):
        """
        Register handler that will be called on disconnect.
        """
        self.disconnect_handlers.append(handler)

    def disconnected(self):
        """
        Called on disconnection. Calls disconnect handlers and cleans things up.
        """
        self.connected = None
        logger.warning('disconnect detected')
        for handler in self.disconnect_handlers:
            handler()

    def event(self, name, args=None):
        raise NotImplementedError('event handler not overridden')

    def is_connected(self):
        return self.connected

    def connect(self, server=None):
        """
        Make a tcp/ip connection, protect it with tls/ssl if possible and start XMPP stream.
        """
        if not server:
            server = (self.server, self.port)
        sock = transports.TCPSocket(server)
        connected = sock.attach(self)
        if not connected:
            sock.remove()
            return None
        self.server = server
        self.connected = True
        self.dispatcher.attach(self)

        while self.dispatcher.stream.document_attrs is None:
            if not self.process(1):
                return None
        document_attrs = self.dispatcher.stream.document_attrs
        if 'version' in document_attrs and document_attrs['version'] == "1.0":
            while not self.dispatcher.stream.features and self.process(1):
                pass
        return self.connected

    def process(self, _):
        raise NotImplementedError('process')

    def auth(self, user, password):
        return auth.NonSASL(user, password).attach(self)