#!/usr/bin/env python2
# coding: utf-8

# vk4xmpp gateway, v1.9
# © simpleApps, 01.08.2013
# Program published under MIT license.
# code cleaned by Ernado, cydev

import signal
import socket
import log
import os

from errors import AuthenticationException, ConnectionError, all_errors


from config import (PID_FILE, DATABASE_FILE,
                    HOST, SERVER, PORT, TRANSPORT_ID,
                    DEBUG_XMPPPY, PASSWORD)

from database import init_db, init_users, set_burst, reset_online_users

# Setup logger
logger = log.get_logger()

socket.setdefaulttimeout(10)

import library.xmpp as xmpp
import handlers
from extensions import message
from daemon import get_pid
from run import run_thread
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


def disconnect_handler(crash=True):
    logger.debug('Handling disconnect. Crash: %s' % crash)

    # if crash:
    #     dump_crash("main.disconnect")

    disconnect_transport()

    exit()




def authenticate():
    """
    Authenticate to jabber server
    """

    logger.debug('Authenticating')
    result =  g.component.auth(TRANSPORT_ID, PASSWORD)

    if not result:
        raise AuthenticationException('Unable to authenticate with provided credentials')

    logger.info('Authenticated')

def connect():
    """
    Connects to jabber server
    """

    logger.debug('Connecting')
    result = g.connect(SERVER, PORT)

    if not result:
        raise ConnectionError

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

    logger.info('Registering handlers')

    g.register_handler("iq", handlers.IQHandler)
    g.register_handler("presence", handlers.PresenceHandler)
    g.register_handler("message", handlers.MessageHandler)
    g.register_disconnect_handler(disconnect_handler)
    g.register_parser(message.parse_message)

    # TODO: Group chats

    init_users(g)
    reset_online_users()

    logger.info('Initialization finished')


def map_clients(f):
    clients = database.get_users()
    map(f, clients)


def halt_handler(sig=None, frame=None):
    status = "Shutting down by %s" % ("SIGTERM" if sig == 15 else "SIGINT")
    logger.debug("%s" % status)

    def send_unavailable_presence(client):
        presence_status = "unavailable"
        user_api.send_presence(g, client, TRANSPORT_ID, presence_status, reason=status)
        # send_presence(client.jidFrom, TRANSPORT_ID, presence_status, reason=status)

    map_clients(send_unavailable_presence)

    try:
        os.remove(PID_FILE)
    except OSError:
        logger.error('unable to remove pid file %s' % PID_FILE)
    exit(sig)

def component_loop():
    logger.debug('component loop started')
    while True:
        try:
            g.component.iter(2)
        # except AttributeError as e:
        #     logger.critical('AttributeError while iterating: %s' % e)
        #     # disconnect_transport()
        #     # disconnect_handler(False)
        #     # break
        #     raise
        except xmpp.StreamError as e:
            logger.critical('StreamError while iterating: %s' % e)
            raise

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, halt_handler)
    signal.signal(signal.SIGINT, halt_handler)

    try:
        initialize()
    except AuthenticationException:
        disconnect_transport()
    except all_errors as e:
        logger.critical('Unable to initialize: %s' % e)
        raise

    run_thread(g.main_loop)
    run_thread(component_loop)

    #
    # while True:
    #     try:
    #         g.component.iter(2)
    #     # except AttributeError as e:
    #     #     logger.critical('AttributeError while iterating: %s' % e)
    #     #     # disconnect_transport()
    #     #     # disconnect_handler(False)
    #     #     # break
    #     #     raise
    #     except xmpp.StreamError as e:
    #         logger.critical('StreamError while iterating: %s' % e)
    #         raise
    #         # dump_crash("Component.iter")
    #     # except Exception as e:
    #     #     logger.critical("DISCONNECTED: %s" % e)
    #     #     dump_crash("Component.iter")
    #     #     disconnect_handler(False)
