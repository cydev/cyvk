#!/usr/bin/env python2
# coding: utf-8
from __future__ import unicode_literals

import signal
import threading
import time

from events.handler import EventHandler
import log
from errors import AuthenticationException, all_errors, ConnectionError
from friends import get_friend_jid
from database import initialize_database
from config import (DATABASE_FILE,
                    HOST, SERVER, PORT, TRANSPORT_ID, PASSWORD)
from parallel import realtime
from parallel.probe import probe_users
from handlers import message_handler, presence_handler
from thandlers import iq_handler
from transport.stanza_queue import enqueue
from parallel.long_polling import start_thread_lp_requests, start_thread_lp
import user as user_api
import xmpp


logger = log.get_logger()


def get_disconnect_handler(c):
    def handler():
        logger.debug('handling disconnect')
        c.disconnect()

    return handler


def authenticate(c):
    """
    Authenticate to jabber server
    """

    logger.debug('authenticating')
    result = c.auth(TRANSPORT_ID, PASSWORD)

    if not result:
        raise AuthenticationException('unable to authenticate with provided credentials')

    logger.info('authenticated')


def connect(c):
    """
    Connects to jabber server
    """

    logger.debug('Connecting')
    r = c.connect((SERVER, PORT))

    if not r:
        raise ConnectionError('unable to connect to %s:%s' % (SERVER, PORT))

    logger.info('Connected')


def get_transport():
    return xmpp.Component(HOST)


def register_handler(c, name, handler):
    c.register_handler(name, handler)


def initialize():
    initialize_database(DATABASE_FILE)
    transport = get_transport()
    connect(transport)
    authenticate(transport)
    logger.info('registering handlers')
    register_handler(transport, "iq", iq_handler)
    register_handler(transport, "presence", presence_handler)
    # register_handler(transport, "message", message_handler)
    realtime.reset_online_users()
    logger.info('initialization finished')

    return transport


def halt_handler(sig=None, _=None):
    status = 'shutting down'
    logger.debug("%s" % status)

    def send_unavailable_presence(jid):
        presence_status = "unavailable"
        friends = realtime.get_friends(jid)
        for friend in friends:
            user_api.send_presence(jid, get_friend_jid(friend), presence_status, reason=status)
        user_api.send_presence(jid, TRANSPORT_ID, presence_status, reason=status)

    clients = realtime.get_clients()
    map(send_unavailable_presence, clients)
    time.sleep(1)
    exit(sig)


def get_transport_iteration(c):
    c.process()


def get_sender_iteration(c):
    stanza = enqueue()
    c.send(stanza)


def get_main_iteration(_):
    user_api.process_users()
    time.sleep(6)


def start_thread(component, target, name):
    logger.debug('starting %s' % name)

    def thread_function(c):
        while True:
            target(c)

    t = threading.Thread(target=thread_function, args=(component, ), name=name)
    t.daemon = True
    t.start()

    return t


def start():
    signal.signal(signal.SIGTERM, halt_handler)
    signal.signal(signal.SIGINT, halt_handler)

    try:
        component = initialize()
        c = component
        h = EventHandler()
        start_thread(c, get_transport_iteration, 'transport loop')
        start_thread(c, get_sender_iteration, 'sender loop')
        start_thread(c, get_main_iteration, 'main loop')
        start_thread_lp_requests()
        start_thread_lp()
        h.start()
        probe_users()
    except all_errors as e:
        logger.critical('unable to initialize: %s' % e)
        halt_handler()
        time.sleep(2)
        exit()

    while True:
        # allow main thread to catch ctrl+c
        time.sleep(1)


if __name__ == "__main__":
    start()
