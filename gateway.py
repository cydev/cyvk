#!/usr/bin/env python2
# coding: utf-8
from __future__ import unicode_literals

import signal
import log
import os
import threading
import time

from errors import AuthenticationException, all_errors
from friends import get_friend_jid
from database import init_db, init_users, set_burst, reset_online_users
from config import (PID_FILE, DATABASE_FILE,
                    HOST, SERVER, PORT, TRANSPORT_ID,
                    DEBUG_XMPPPY, PASSWORD)


logger = log.get_logger()

import library.xmpp as xmpp
import handlers
from extensions import message
from daemon import get_pid
from singletone import Gateway
import database
import user as user_api

g = Gateway()

def disconnect_transport():
    logger.debug('disconnecting transport')
    try:
        if g.component.isConnected():
            g.component.disconnect()
        return True
    except (NameError, AttributeError):
        return False


def disconnect_handler():
    logger.debug('handling disconnect')
    disconnect_transport()


def authenticate():
    """
    Authenticate to jabber server
    """

    logger.debug('authenticating')
    result =  g.component.auth(TRANSPORT_ID, PASSWORD)

    if not result:
        raise AuthenticationException('unable to authenticate with provided credentials')

    logger.info('authenticated')

def connect():
    """
    Connects to jabber server
    """

    logger.debug('Connecting')
    g.connect(SERVER, PORT)
    logger.info('Connected')


def get_transport():
    return xmpp.Component(HOST, debug=DEBUG_XMPPPY)


def initialize():
    get_pid(PID_FILE)
    init_db(DATABASE_FILE)
    set_burst()

    g.component = get_transport()

    connect()
    authenticate()

    logger.info('registering handlers')

    g.register_handler("iq", handlers.IQHandler)
    g.register_handler("presence", handlers.PresenceHandler)
    g.register_handler("message", handlers.MessageHandler)
    g.register_disconnect_handler(disconnect_handler)
    g.register_parser(message.parse_message)

    # TODO: Group chats

    init_users(g)
    reset_online_users()

    logger.info('initialization finished')


def map_clients(f):
    clients = database.get_users()
    map(f, clients)


def get_loop_thread(iteration_handler, name, iteration_time=0):

    def iteration():
        while True:
            iteration_handler()
            time.sleep(iteration_time)

    thread = threading.Thread(target=iteration, name=name)
    thread.daemon = True

    return thread

def halt_handler(sig=None, frame=None):
    status = "shutting down by %s" % ("SIGTERM" if sig == 15 else "SIGINT")
    logger.debug("%s" % status)

    def send_unavailable_presence(jid):
        presence_status = "unavailable"
        friends = database.get_friends(jid)
        for friend in friends:
           user_api.send_presence(g, jid, get_friend_jid(friend, jid), presence_status, reason=status)
        user_api.send_presence(g, jid, TRANSPORT_ID, presence_status, reason=status)
        # send_presence(client.jidFrom, TRANSPORT_ID, presence_status, reason=status)

    map_clients(send_unavailable_presence)
    disconnect_transport()

    try:
        os.remove(PID_FILE)
    except OSError:
        logger.error('unable to remove pid file %s' % PID_FILE)
    exit(sig)

def transport_iteration():
    try:
        g.component.iter(2)
    except xmpp.StreamError as e:
        logger.critical('StreamError while iterating: %s' % e)
        raise

def component_loop():
    logger.debug('component loop started')

    while True:
        transport_iteration()

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, halt_handler)
    signal.signal(signal.SIGINT, halt_handler)

    try:
        initialize()
    except all_errors as e:
        logger.critical('unable to initialize: %s' % e)
        halt_handler()

    main_loop = get_loop_thread(g.main_loop_iteration, 'main loop', 5)
    transport_loop = get_loop_thread(transport_iteration, 'transport loop')

    main_loop.start()
    transport_loop.start()

    while True:
        # allow main thread to catch ctrl+c
        time.sleep(1)

