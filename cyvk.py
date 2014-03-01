import signal
from time import time

import gevent
from gevent.queue import Queue

from wrappers import asynchronous
from config import HOST, PASSWORD, PORT, TRANSPORT_ID, DB_FILE
from cystanza.stanza import Probe, UnavailablePresence
from database import initialize_database, get_all_users
from friends import get_friend_jid
import xmpp
from log import get_logger


logger = get_logger()


def loop(f):
    @asynchronous
    def wrapper(*args, **kwargs):
        while True:
            f(*args, **kwargs)

    return wrapper


class CyVk(object):
    def __init__(self):
        self.users = {}
        self.client = xmpp.Component(self, HOST)
        self.sending = Queue(100)
        self.dispatcher_gl = None
        gevent.signal(signal.SIGTERM, self.disconnect)
        gevent.signal(signal.SIGINT, self.disconnect)

    def disconnect(self):
        for user in self.users.values():
            for friend in user.friends:
                self.send(UnavailablePresence(get_friend_jid(friend), user.jid))
            self.send(UnavailablePresence(TRANSPORT_ID, user.jid))
        while not self.sending.empty():
            gevent.sleep(0.1)
        self.client.connection.disconnect()
        exit(1)

    def connect(self):
        logger.debug('starting connecting')
        connected = self.client.connect(HOST, PORT)
        if not connected:
            return logger.debug('not connected')
        logger.debug('connected')
        self.client.auth(TRANSPORT_ID, PASSWORD)
        logger.debug('auth')

    @staticmethod
    def run_forever():
        while True:
            gevent.sleep(0.25)

    def start(self):
        initialize_database(DB_FILE)
        s = gevent.spawn(self.run_forever)
        self.connect()
        self.dispatcher_loop()
        self.receiver_loop()
        self.probe_users()
        self.process_users()
        s.join()

    @loop
    def dispatcher_loop(self):
        self.client.process()

    @loop
    def receiver_loop(self):
        d = self.sending.get()
        logger.debug('trying to send %s' % d)
        self.client.send(d)

    def add_user(self, user):
        self.users.update({user.jid: user})

    def send(self, stanza):
        logger.debug('adding to queue %s' % stanza)
        self.sending.put(stanza, block=False)
        logger.debug('added to queue')

    @asynchronous
    def probe_users(self):
        all_users = get_all_users()
        for user in all_users:
            try:
                jid = user[0]
            except (KeyError, ValueError, IndexError) as e:
                logger.error('%s while sending probes' % e)
                continue
            self.send(Probe(TRANSPORT_ID, jid))

    @loop
    def process_users(self):
        now = time()

        if not self.users:
            logger.debug('no clients')

        for user in self.users.values():
            gevent.spawn(user.process)

        logger.debug('iterated for %.2f ms' % ((time() - now) * 1000))
        gevent.sleep(6)


if __name__ == '__main__':
    transport = CyVk()
    transport.start()
