#!/usr/bin/env python2
# coding: utf-8

# vk4xmpp gateway, v1.9
# © simpleApps, 01.08.2013
# Program published under MIT license.

import signal
import socket
import threading
import log
import sys
import os
import time


from config import (THREAD_STACK_SIZE,
                    PID_FILE, DATABASE_FILE,
                    HOST, SERVER, PORT, TRANSPORT_ID,
                    DEBUG_XMPPPY, PASSWORD)

from database import init_db, init_users

# Setup logger
logger = log.get_logger()

reload(sys).setdefaultencoding("utf-8")
socket.setdefaulttimeout(10)

import library.xmpp as xmpp
import handlers
from extensions import message
from library.writer import dump_crash
from daemon import get_pid


if THREAD_STACK_SIZE:
    threading.stack_size(THREAD_STACK_SIZE)

from singletone import Gateway

g = Gateway()

def disconnect_handler(crash=True):
    if crash:
        dump_crash("main.disconnect")
    try:
        if g.component.isConnected():
            g.component.disconnect()
    except (NameError, AttributeError):
        pass
    sleep_seconds = 5
    logger.debug("Reconnecting in %s seconds" % sleep_seconds)
    time.sleep(sleep_seconds)
    os.execl(sys.executable, sys.executable, *sys.argv)

def main():
    get_pid(PID_FILE)
    init_db(DATABASE_FILE)

    g.component = xmpp.Component(HOST, debug=DEBUG_XMPPPY)

    if not g.connect(SERVER, PORT):
        return

    if not g.component.auth(TRANSPORT_ID, PASSWORD):
        logger.debug("Auth failed (%s/%s)!\n" % (g.component.lastErr, g.component.lastErrCode))
        disconnect_handler(False)
        return

    logger.info('Auth ok')
    logger.info('Registering handlers')

    g.register_handler("iq", handlers.IQHandler)
    g.register_handler("presence", handlers.PresenceHandler)
    g.register_handler("message", handlers.MessageHandler)
    g.register_disconnect_handler(disconnect_handler)
    g.register_parser(message.parse_message)

    # TODO: Group chats

    init_users(g)

    logger.info('Initialization finished')


def stop(sig=None, frame=None):
    status = "Shutting down by %s" % ("SIGTERM" if sig == 15 else "SIGINT")
    logger.debug("%s" % status)
    for client in g.clients:
        client.send_presence(client.jidFrom, TRANSPORT_ID, "unavailable", reason=status)
        logger.debug("." * len(client.friends))
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    exit(sig)


# def garbageCollector():
#     while True:
#         gc.collect()
#         time.sleep(60)


lengthOfTransportsList = 0

if __name__ == "__main__":
    # run_thread(garbageCollector, (), "gc")
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    main()

    while True:
        try:
            g.component.iter(2)
        except AttributeError:
            disconnect_handler(False)
            break
        except xmpp.StreamError:
            dump_crash("Component.iter")
        except Exception as e:
            logger.critical("DISCONNECTED: %s" % e)
            dump_crash("Component.iter")
            disconnect_handler(False)
