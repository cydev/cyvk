#!/usr/bin/env python2
# coding: utf-8
from __future__ import unicode_literals

import signal
import log
import os
import threading
from multiprocessing import Process
import time

from errors import AuthenticationException, all_errors, ConnectionError
from friends import get_friend_jid
from database import initialize_database, probe_users, initialize_burst_protection, reset_online_users
from config import (PID_FILE, DATABASE_FILE,
                    HOST, SERVER, PORT, TRANSPORT_ID,
                    DEBUG_XMPPPY, PASSWORD)


logger = log.get_logger()

import library.xmpp as xmpp
import handlers
from daemon import get_pid
import database
import user as user_api


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
    result =  c.auth(TRANSPORT_ID, PASSWORD)

    if not result:
        raise AuthenticationException('unable to authenticate with provided credentials')

    logger.info('authenticated')

def connect(c):
    """
    Connects to jabber server
    """

    logger.debug('Connecting')
    r =  c.connect((SERVER, PORT))

    if not r:
        raise ConnectionError

    logger.info('Connected')


def get_transport():
    return xmpp.Component(HOST, debug=DEBUG_XMPPPY)


def register_handler(c, name, handler_class):
    c.RegisterHandler(name, handler_class().handle)

def initialize():
    get_pid(PID_FILE)
    initialize_database(DATABASE_FILE)
    initialize_burst_protection()

    transport = get_transport()

    connect(transport)
    authenticate(transport)

    logger.info('registering handlers')

    register_handler(transport, "iq", handlers.IQHandler)
    register_handler(transport, "presence", handlers.PresenceHandler)
    register_handler(transport, "message", handlers.MessageHandler)
    transport.RegisterDisconnectHandler(get_disconnect_handler(transport))

    reset_online_users()

    logger.info('initialization finished')

    return transport


def map_clients(f):
    clients = database.get_clients()
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

def halt_handler(sig=None, frame=None):
    status = "shutting down by %s" % ("SIGTERM" if sig == 15 else "SIGINT")
    logger.debug("%s" % status)

    def send_unavailable_presence(jid):
        presence_status = "unavailable"
        friends = database.get_friends(jid)
        for friend in friends:
           user_api.send_presence(jid, get_friend_jid(friend, jid), presence_status, reason=status)
        user_api.send_presence(jid, TRANSPORT_ID, presence_status, reason=status)
        # send_presence(client.jidFrom, TRANSPORT_ID, presence_status, reason=status)

    map_clients(send_unavailable_presence)
    # disconnect_transport()
    # TODO: send to component thread message to disconnect

    try:
        os.remove(PID_FILE)
    except OSError:
        logger.error('unable to remove pid file %s' % PID_FILE)
    exit(sig)

def get_transport_iteration(c):

    def transport_iteration():
        try:
            c.iter(2)
        except xmpp.StreamError as stream_error:
            logger.critical('StreamError while iterating: %s' % stream_error)
            raise

    return transport_iteration


def get_sender_iteration(c):

    def stanza_sender_iteration():
        stanza = database.enqueue_stanza()
        # noinspection PyUnresolvedReferences
        c.send(stanza)

    return stanza_sender_iteration



if __name__ == "__main__":
    signal.signal(signal.SIGTERM, halt_handler)
    signal.signal(signal.SIGINT, halt_handler)

    try:
        component = initialize()

        # main_loop = get_loop_thread(user_api.main_loop_iteration, 'main loop', 5)
        main_loop = Process(target=get_loop(user_api.process_users,  'main loop', 35), name='main loop')
        # transport_loop = Process(target=transport_loop, args=(component, ), name='transport loop')
        transport_loop = get_loop_thread(get_transport_iteration(component), 'transport loop')
        sender_loop = get_loop_thread(get_sender_iteration(component), 'stanza sender loop')

        main_loop.start()
        transport_loop.start()
        sender_loop.start()

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

