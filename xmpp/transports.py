# coding=utf-8
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
from __future__ import unicode_literals
import socket
from select import select
import logging

from xmpp.simplexml import ustr

logger = logging.getLogger("xmpp")

try:
    import dns
except ImportError:
    dns = None

DATA_RECEIVED = 'DATA RECEIVED'
DATA_SENT = 'DATA SENT'
BUFF_LEN = 1024


class TCPSocket(object):
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
        self._server, self.use_srv = server, use_srv
        self._sock = None
        self._send = None
        self._receive = None
        self._seen_data = None

    def get_host(self):
        return self._server[0]

    def get_port(self):
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

    def receive(self):
        """
        Reads all pending incoming data.
        In case of disconnection calls disconnected() method and then raises IOError exception.
        """
        try:
            data = self._receive(BUFF_LEN)
        except socket.sslerror as e:
            self._seen_data = 0
            if e[0] in (socket.SSL_ERROR_WANT_READ, socket.SSL_ERROR_WANT_WRITE):
                return None
            raise IOError('socket error while receiving data')
        except (IOError, KeyError):
            data = ''
        while self.pending_data(0):
            add = self._receive(BUFF_LEN)
            if not add:
                break
            data += add

        if not data:
            raise IOError("no data received")

        self._seen_data = 1
        logger.debug('got: %s' % data.decode('utf-8'))
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
        try:
            self._send(data)
        except (socket.error, IOError):
            logger.debug('disconnected from server')
            raise
        else:
            if not data.strip():
                data = repr(data)
            logger.debug('sent: %s' % data.decode('utf-8'))

    def pending_data(self, timeout=0):
        """
        Returns true if there is a data ready to be read.
        """
        return select([self._sock], [], [], timeout)[0]

    def disconnect(self):
        """
        Closes the socket.
        """
        logger.debug('closing socket')
        self._sock.close()

    def disconnected(self):
        """
        Called when a Network Error or disconnection occurs.
        Designed to be overridden.
        """
        # logger.error('Socket operation failed')
        raise NotImplementedError('disconnected not implemented')
