##   client.py
##
##   Copyright (C) 2003-2005 Alexey "Snake" Nezhdanov
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.

# $Id: client.py, v1.62 2013/10/21 alkorgun Exp $

"""
Provides PlugIn class functionality to develop extentions for xmpppy.
Also provides Client and Component classes implementations as the
examples of xmpppy structures usage.
These classes can be used for simple applications "AS IS" though.
"""

from xmpp import auth, dispatcher, transports
import logging

logger = logging.getLogger("xmpp")


class CommonClient:
    """
    Base for Client and Component classes.
    """

    def __init__(self, server, port=5222, debug=None):
        """
        Caches server name and (optionally) port to connect to. "debug" parameter specifies
        the debug IDs that will go into debug output. You can either specifiy an "include"
        or "exclude" list. The latter is done via adding "always" pseudo-ID to the list.
        Full list: ["nodebuilder", "dispatcher", "gen_auth", "SASL_auth", "bind", "socket",
        "CONNECTproxy", "TLS", "roster", "browser", "ibb"].
        """
        # if isinstance(self, Client):
        #     self.Namespace, self.DBG = "jabber:client", DBG_CLIENT
        if isinstance(self, Component):
            self.namespace = dispatcher.NS_COMPONENT_ACCEPT

        self.default_namespace = self.namespace
        self.disconnect_handlers = []
        self.server = server
        self.proxy = None
        self.port = port
        self.owner = self
        self.registered_name = None
        self.connected = ""
        self.route = 0
        self.connection = None

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
        Default event handler. To be overriden.
        """
        if not args: args = {}
        print("Event: %s-%s" % (name, args))

    def is_connected(self):
        """
        Returns connection state. F.e.: None / "tls" / "tcp+non_sasl" .
        """
        return self.connected

    def connect(self, server=None, proxy=None, ssl=None, use_srv=False):
        """
        Make a tcp/ip connection, protect it with tls/ssl if possible and start XMPP stream.
        Returns None or "tcp" or "tls", depending on the result.
        """
        if not server:
            server = (self.server, self.port)
        if proxy:
            raise NotImplementedError('proxy')
        else:
            sock = transports.TCPSocket(server, use_srv)
        connected = sock.attach(self)
        if not connected:
            sock.remove()
            return None
        self.server, self.proxy = server, proxy
        self.connected = "tcp"
        dispatcher.Dispatcher().attach(self)
        while self.Dispatcher.stream.document_attrs is None:
            if not self.process(1):
                return None
        document_attrs = self.Dispatcher.stream.document_attrs
        if 'version' in document_attrs and document_attrs['version'] == "1.0":
            while not self.Dispatcher.stream.features and self.process(1):
                pass  # If we get version 1.0 stream the features tag MUST BE presented
        return self.connected

    def process(self, _):
        raise NotImplementedError('process')


class Component(CommonClient):
    """
    Component class. The only difference from CommonClient is ability to perform component authentication.
    """

    def __init__(self, transport, port=5347, typ=None, debug=None, domains=None, sasl=0, bind=0, route=0, xcp=0):
        """
        Init function for Components.
        As components use a different auth mechanism which includes the namespace of the component.
        Jabberd1.4 and Ejabberd use the default namespace then for all client messages.
        Jabberd2 uses jabber:client.
        "transport" argument is a transport name that you are going to serve (f.e. "irc.localhost").
        "port" can be specified if "transport" resolves to correct IP. If it is not then you'll have to specify IP
        and port while calling "connect()".
        If you are going to serve several different domains with single Component instance - you must list them ALL
        in the "domains" argument.
        For jabberd2 servers you should set typ="jabberd2" argument.
        """
        CommonClient.__init__(self, transport, port=port, debug=debug)
        self.typ = typ
        self.sasl = sasl
        self.bind = bind
        self.route = route
        self.xcp = xcp
        if domains:
            self.domains = domains
        else:
            self.domains = [transport]

    def connect(self, server=None, proxy=None):
        """
        This will connect to the server, and if the features tag is found then set
        the namespace to be jabber:client as that is required for jabberd2.
        "server" and "proxy" arguments have the same meaning as in xmpp.Client.connect().
        """
        if self.sasl:
            self.namespace = auth.NS_COMPONENT_1
            self.server = server[0]
        CommonClient.connect(self, server=server, proxy=proxy)
        if self.connected and (
                        self.typ == "jabberd2" or not self.typ and self.Dispatcher.stream.features is not None) and (
                not self.xcp):
            self.default_namespace = auth.NS_CLIENT
            self.Dispatcher.register_namespace(self.default_namespace)
            self.Dispatcher.register_protocol("iq", dispatcher.Iq)
            self.Dispatcher.register_protocol("message", dispatcher.Message)
            self.Dispatcher.register_protocol("presence", dispatcher.Presence)
        return self.connected

    def auth(self, name, password, dup=None):
        """
        Authenticate component "name" with password "password".
        """
        self._User, self._Password, self._Resource = name, password, ""
        if auth.NonSASL(name, password, "").attach(self):
            self.connected += "+old_auth"
            return "old_auth"
        return None

