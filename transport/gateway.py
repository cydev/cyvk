#!/usr/bin/env python2
# coding: utf-8
from __future__ import unicode_literals

import signal
import threading
import time
from events.handler import EventHandler
from handlers.presence import PresenceHandler

import log
from errors import AuthenticationException, all_errors, ConnectionError
from friends import get_friend_jid
from database import initialize_database
from config import (PID_FILE, DATABASE_FILE,
                    HOST, SERVER, PORT, TRANSPORT_ID,
                    DEBUG_XMPPPY, PASSWORD)
from parallel import realtime
from parallel.probe import probe_users
from transport import user as user_api, _handlers
from transport.stanza_queue import enqueue
from parallel.long_polling import loop as long_polling_loop_func
from parallel.long_polling import loop_for_starting

logger = log.get_logger()

import xmpp


def get_disconnect_handler(c):
    def handler():
        logger.debug('handling disconnect')
        if c.isConnected():
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
    return xmpp.Component(HOST, debug=DEBUG_XMPPPY)


def register_handler(c, name, handler_class):
    c.RegisterHandler(name, handler_class().handle)


def initialize():
    initialize_database(DATABASE_FILE)

    transport = get_transport()

    connect(transport)
    authenticate(transport)

    logger.info('registering handlers')

    register_handler(transport, "iq", _handlers.IQHandler)
    register_handler(transport, "presence", PresenceHandler)
    register_handler(transport, "message", _handlers.MessageHandler)
    transport.RegisterDisconnectHandler(get_disconnect_handler(transport))
    realtime.reset_online_users()

    logger.info('initialization finished')

    return transport


def map_clients(f):
    clients = realtime.get_clients()
    map(f, clients)


def get_loop(iteration_handler, name, iteration_time=0):
    def loop():
        logger.debug('starting %s' % name)
        while True:
            iteration_handler()
            time.sleep(iteration_time)

    return loop


def get_loop_thread(iteration_handler, name, iteration_time=0):
    thread = threading.Thread(target=get_loop(iteration_handler, name, iteration_time), name=name)
    thread.daemon = True

    return thread


def halt_handler(sig=None, _=None):
    status = 'shutting down'
    logger.debug("%s" % status)

    def send_unavailable_presence(jid):
        presence_status = "unavailable"
        friends = realtime.get_friends(jid)
        for friend in friends:
            user_api.send_presence(jid, get_friend_jid(friend), presence_status, reason=status)
        user_api.send_presence(jid, TRANSPORT_ID, presence_status, reason=status)
        # send_presence(client.jidFrom, TRANSPORT_ID, presence_status, reason=status)

    map_clients(send_unavailable_presence)
    # disconnect_transport()
    # TODO: send to component thread message to disconnect

    # try:
    #     os.remove(PID_FILE)
    # except OSError:
    #     logger.error('unable to remove pid file %s' % PID_FILE)
    exit(sig)


def get_transport_iteration(c):
    def transport_iteration():
        try:
            c.Process()
        except xmpp.StreamError as stream_error:
            logger.critical('StreamError while iterating: %s' % stream_error)
            raise

    return transport_iteration


def get_sender_iteration(c):
    def stanza_sender_iteration():
        stanza = enqueue()
        # noinspection PyUnresolvedReferences
        c.send(stanza)

    return stanza_sender_iteration


def start():
    signal.signal(signal.SIGTERM, halt_handler)
    signal.signal(signal.SIGINT, halt_handler)

    try:
        component = initialize()
        h = EventHandler()
        # main_loop = get_loop_thread(user_api.main_loop_iteration, 'main loop', 5)
        main_loop = threading.Thread(target=get_loop(user_api.process_users, 'main loop', 35), name='main loop')
        main_loop.daemon = True
        # transport_loop = Process(target=transport_loop, args=(component, ), name='transport loop')
        transport_loop = get_loop_thread(get_transport_iteration(component), 'transport loop')
        sender_loop = get_loop_thread(get_sender_iteration(component), 'stanza sender loop')
        long_polling_loop = threading.Thread(target=long_polling_loop_func, name='long polling loop')
        long_polling_loop.daemon = True

        long_polling_start_loop = threading.Thread(target=loop_for_starting, name='long polling starting loop')
        long_polling_start_loop.daemon = True

        h.start()
        sender_loop.start()
        transport_loop.start()
        main_loop.start()
        long_polling_start_loop.start()
        # long_polling_loop.start()

        # probe all users from database and add them to client list
        # if they are online
        time.sleep(0.5)
        probe_users()
    except all_errors as e:
        logger.critical('unable to initialize: %s' % e)
        halt_handler()
        exit()

    while True:
        # allow main thread to catch ctrl+c
        time.sleep(1)


if __name__ == "__main__":
    start()


