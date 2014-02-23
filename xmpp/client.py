"""
Provides PlugIn class functionality to develop extentions for xmpppy.
Also provides Client and Component classes implementations as the
examples of xmpppy structures usage.
These classes can be used for simple applications "AS IS" though.
"""
from xmpp import auth, dispatcher, transports
import logging
logger = logging.getLogger("xmpp")


class CommonClient(object):
    """
    Base for Client and Component classes.
    """

    def __init__(self, server, port=5222):
        """
        Caches server name and (optionally) port to connect to. "debug" parameter specifies
        the debug IDs that will go into debug output. You can either specifiy an "include"
        or "exclude" list. The latter is done via adding "always" pseudo-ID to the list.
        Full list: ["nodebuilder", "dispatcher", "gen_auth", "SASL_auth", "bind", "socket",
        "CONNECTproxy", "TLS", "roster", "browser", "ibb"].
        """
        if isinstance(self, Component):
            self.namespace = dispatcher.NS_COMPONENT_ACCEPT

        self.default_namespace = self.namespace
        self.disconnect_handlers = []
        self.server = server
        self.port = port
        self.owner = self
        self.registered_name = None
        self.connected = ''
        self.connection = None
        self.user = None
        self.password = None
        self.resource = None
        self.dispatcher = dispatcher.Dispatcher()

    def register_disconnect_handler(self, handler):
        """
        Register handler that will be called on disconnect.
        """
        self.disconnect_handlers.append(handler)

    def disconnected(self):
        """
        Called on disconnection. Calls disconnect handlers and cleans things up.
        """
        self.connected = ""

        logger.warning('disconnect detected')
        self.disconnect_handlers.reverse()

        for handler in self.disconnect_handlers:
            handler()

        self.disconnect_handlers.reverse()

    def event(self, name, args=None):
        """
        Default event handler. To be overridden.
        """
        raise NotImplementedError('event handler not overridden')

    def is_connected(self):
        """
        Returns connection state. F.e.: None / "tls" / "tcp+non_sasl" .
        """
        return self.connected

    def connect(self, server=None):
        """
        Make a tcp/ip connection, protect it with tls/ssl if possible and start XMPP stream.
        Returns None or "tcp" or "tls", depending on the result.
        """
        if not server:
            server = (self.server, self.port)
        sock = transports.TCPSocket(server)
        connected = sock.attach(self)
        if not connected:
            sock.remove()
            return None
        self.server = server
        self.connected = "tcp"
        self.dispatcher.attach(self)

        while self.dispatcher.stream.document_attrs is None:
            if not self.process(1):
                return None
        document_attrs = self.dispatcher.stream.document_attrs
        if 'version' in document_attrs and document_attrs['version'] == "1.0":
            while not self.dispatcher.stream.features and self.process(1):
                pass  # If we get version 1.0 stream the features tag MUST BE presented
        return self.connected

    def process(self, _):
        raise NotImplementedError('process')


class Component(CommonClient):
    """
    Component class. The only difference from CommonClient is ability to perform component authentication.
    """

    def __init__(self, transport, port=5347):
        super(Component, self).__init__(transport, port)
        self.domains = [transport, ]

    def connect(self, server=None, proxy=None):
        super(Component, self).connect(server)
        return self.connected

    def auth(self, user, password):
        self.user, self.password, self.resource = user, password, ''
        if auth.NonSASL(user, password, '').attach(self):
            self.connected += "+old_auth"
            return "old_auth"
        return None
