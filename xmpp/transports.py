##   transports.py
##
##   Copyright (C) 2003-2004 Alexey "Snake" Nezhdanov
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

# $Id: transports.py, v1.36 2013/11/03 alkorgun Exp $

"""
This module contains the low-level implementations of xmpppy connect methods or
(in other words) transports for xmpp-stanzas.
Currently here is three transports:
direct TCP connect - TCPsocket class
proxied TCP connect - HTTPPROXYsocket class (CONNECT proxies)
TLS connection - TLS class. Can be used for SSL connections also.

Transports are stackable so you - f.e. TLS use HTPPROXYsocket or TCPsocket as more low-level transport.

Also exception 'error' is defined to allow capture of this module specific exceptions.
"""

import sys
import socket
from select import select
import logging

from xmpp.simplexml import ustr
from xmpp.plugin import PlugIn

logger = logging.getLogger("xmpp")

try:
    import dns
except ImportError:
    dns = None

DATA_RECEIVED = 'DATA RECEIVED'
DATA_SENT = 'DATA SENT'
BUFF_LEN = 1024


class Error:
    """
    An exception to be raised in case of low-level errors in methods of 'transports' module.
    """

    def __init__(self, comment):
        """
        Cache the descriptive string.
        """
        self._comment = comment

    def __str__(self):
        """
        Serialize exception into pre-cached descriptive string.
        """
        return self._comment


class TCPSocket(PlugIn):
    """
    This class defines direct TCP connection method.
    """

    def __init__(self, server=None, use_srv=True):
        """
        Cache connection point 'server'. 'server' is the tuple of (host, port)
        absolutely the same as standard tcp socket uses. However library will lookup for
        ('_xmpp-client._tcp.' + host) SRV record in DNS and connect to the found (if it is)
        server instead.
        """
        PlugIn.__init__(self)
        self._exported_methods = [self.send, self.disconnect]
        self._server, self.use_srv = server, use_srv
        self._sock = None
        self._send = None
        self._receive = None
        self._seen_data = None

    @staticmethod
    def srv_lookup(server):
        """
        SRV resolver. Takes server=(host, port) as argument. Returns new (host, port) pair.
        """
        if not dns:
            return server
        query = '_xmpp-client._tcp.%s' % server[0]
        try:
            dns.DiscoverNameServers()
            dns__ = dns.Request()
            response = dns__.req(query, qtype='SRV')
            if response.answers:
                (port, host) = response.answers[0]['data'][2:]
                server = str(host), int(port)
        except dns.DNSError:
            logger.error('An error occurred while looking up %s.' % query)
        return server

    def plugin(self, owner):
        """
        Fire up connection. Return non-empty string on success.
        Also registers self.disconnected method in the owner's dispatcher.
        Called internally.
        """
        if not self._server:
            self._server = (self.owner.Server, 5222)
        if self.use_srv:
            server = self.srv_lookup(self._server)
        else:
            server = self._server
        if not self.connect(server):
            return None
        self.owner.connection = self
        self.owner.register_disconnect_handler(self.disconnected)
        return "ok"

    def get_host(self):
        """
        Returns the 'host' value that is connection is [will be] made to.
        """
        return self._server[0]

    def get_port(self):
        """
        Returns the 'port' value that is connection is [will be] made to.
        """
        return self._server[1]

    def connect(self, server=None):
        """
        Try to connect to the given host/port. Does not lookup for SRV record.
        Returns non-empty string on success.
        """
        host, port = server
        server = (host, int(port))
        if ":" in host:
            sock = socket.AF_INET6
            server = server.__add__((0, 0))
        else:
            sock = socket.AF_INET
        try:
            self._sock = socket.socket(sock, socket.SOCK_STREAM)
            self._sock.connect(server)
            self._send = self._sock.sendall
            self._receive = self._sock.recv
        except socket.error as error:
            try:
                code, error = error
            except (ValueError, TypeError):
                code = -1
            logger.error('Failed to connect to remote host %s: %s (%s)' % (repr(server), error, code))
        else:
            logger.debug("Successfully connected to remote host %s." % repr(server))
            return 'ok'

    def plugout(self):
        """
        Disconnect from the remote server and unregister self.disconnected method from
        the owner's dispatcher.
        """
        self._sock.close()
        if hasattr(self.owner, "Connection"):
            del self.owner.Connection
            self.owner.UnregisterDisconnectHandler(self.disconnected)

    def receive(self):
        """
        Reads all pending incoming data.
        In case of disconnection calls owner's disconnected() method and then raises IOError exception.
        """
        try:
            data = self._receive(BUFF_LEN)
        except socket.sslerror as e:
            self._seen_data = 0
            if e[0] in (socket.SSL_ERROR_WANT_READ, socket.SSL_ERROR_WANT_WRITE):
                return ''
            logger.error('Socket error while receiving data')
            sys.exc_clear()
            self.owner.disconnected()
            raise IOError('disconnected')
        except Exception:
            data = ''
        while self.pending_data(0):
            try:
                add = self._receive(BUFF_LEN)
            except Exception:
                break
            if not add:
                break
            data += add
        if data:
            self._seen_data = 1
            logger.debug('got: %s' % data)
            if hasattr(self.owner, "Dispatcher"):
                self.owner.Dispatcher.event("", DATA_RECEIVED, data)
        else:
            logger.error('Socket error while receiving data')
            sys.exc_clear()
            self.owner.disconnected()
            raise IOError("Disconnected!")
        return data

    def send(self, data, timeout=0.002):
        """
        Writes raw outgoing data. Blocks until done.
        If supplied data is unicode string, encodes it to utf-8 before send.
        """
        if isinstance(data, unicode):
            data = data.encode("utf-8")
        elif not isinstance(data, str):
            data = ustr(data).encode("utf-8")
        while not select((), [self._sock], (), timeout)[1]:
            pass
        else:
            try:
                self._send(data)
            except Exception:
                logger.debug('Socket error while sending data')
                self.owner.disconnected()
            else:
                if not data.strip():
                    data = repr(data)
                logger.debug('sent: %s' % data)
                if hasattr(self.owner, "Dispatcher"):
                    self.owner.Dispatcher.event("", DATA_SENT, data)

    def pending_data(self, timeout=0):
        """
        Returns true if there is a data ready to be read.
        """
        return select([self._sock], [], [], timeout)[0]

    def disconnect(self):
        """
        Closes the socket.
        """
        logger.debug('Closing socket')
        self._sock.close()

    def disconnected(self):
        """
        Called when a Network Error or disconnection occurs.
        Designed to be overridden.
        """
        # logger.error('Socket operation failed')
        raise NotImplementedError('disconnected not implemented')
