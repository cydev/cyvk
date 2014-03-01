# coding=utf-8
from __future__ import unicode_literals
from socket import AF_INET, SOCK_STREAM, error as socket_error
import logging

from gevent import socket
from gevent.select import select

from wrappers import asynchronous


logger = logging.getLogger("xmpp")
BUFF_LEN = 1024


class TCPSocket(object):
    """This class defines direct TCP connection method."""

    def __init__(self):
        self._sock = None

    def connect(self, host, port):
        """Try to connect to the given host/port. Does no lookup for SRV record."""
        server = (host, int(port))
        try:
            self._sock = socket.create_connection(server)
        except socket_error as error:
            logger.error('Failed to connect to %s:%s (%s)' % (host, port, error))
            return False
        else:
            logger.debug("Successfully connected to host %s:%s" % (host, port))
            return True

    def receive(self):
        """Reads all pending incoming data"""
        logger.debug('socket: receiving')
        socket.wait_read(self._sock.fileno())
        try:
            data = self._sock.recv(BUFF_LEN)
        except (IOError, KeyError):
            data = ''
        logger.debug('socket: received')
        while True:
            is_more = self.pending_data(0)
            if is_more:
                logger.debug('there is data')
            else:
                logger.debug('no more data')
                break
            add = self._sock.recv(BUFF_LEN)
            data += add
        logger.debug('got: %s' % data.decode('utf-8'))
        return data

    @asynchronous
    def process(self):
        logger.debug('processing')

    def send(self, data):
        """Writes raw outgoing data. Blocks until done."""
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        elif not isinstance(data, str):
            data = str(data)
        socket.wait_write(self._sock.fileno())
        try:
            self._sock.sendall(data)
            logger.debug('sent: %s' % str(data).decode('utf-8'))
        except (socket_error, IOError):
            logger.debug('disconnected from server')
            raise

    def pending_data(self, timeout=0):
        """Returns true if there is a data ready to be read"""
        if timeout:
            logger.debug('waiting for data %s seconds' % timeout)
        # return socket.wait_read(self._sock.fileno())
        x = select([self._sock], [], [], timeout)
        logger.debug('select result: %s' % repr(x))
        return x[0]

    def disconnect(self):
        """Closes the socket"""
        logger.debug('closing socket')
        self._sock.close()
