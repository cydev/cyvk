# coding=utf-8
from __future__ import unicode_literals
# from gevent.monkey import patch_all
#
# patch_all()

import socket
from select import select
import logging

logger = logging.getLogger("xmpp")
BUFF_LEN = 1024


class TCPSocket(object):
    """This class defines direct TCP connection method."""

    def __init__(self, server=None, use_srv=True):
        self._server, self.use_srv = server, use_srv
        self._sock = None
        self._send = None
        self._receive = None

    def get_host(self):
        return self._server[0]

    def get_port(self):
        return self._server[1]

    def connect(self, server=None):
        """Try to connect to the given host/port. Does no lookup for SRV record."""
        host, port = server
        server = (host, int(port))
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect(server)
            self._send = self._sock.sendall
            self._receive = self._sock.recv
        except socket.error as error:
            logger.error('Failed to connect to remote host %s: %s' % (repr(server), error))
        else:
            logger.debug("Successfully connected to remote host %s." % repr(server))
            return True

    def receive(self):
        """Reads all pending incoming data"""
        try:
            data = self._receive(BUFF_LEN)
        except socket.sslerror as e:
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
        logger.debug('got: %s' % data.decode('utf-8'))
        return data

    def send(self, data, timeout=0.002):
        """Writes raw outgoing data. Blocks until done."""
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        elif not isinstance(data, str):
            data = str(data)
        while not select((), [self._sock], (), timeout)[1]:
            pass
        try:
            self._send(data)
            logger.debug('sent: %s' % str(data).decode('utf-8'))
        except (socket.error, IOError):
            logger.debug('disconnected from server')
            raise

    def pending_data(self, timeout=0):
        """Returns true if there is a data ready to be read"""
        return select([self._sock], [], [], timeout)[0]

    def disconnect(self):
        """Closes the socket"""
        logger.debug('closing socket')
        self._sock.close()
