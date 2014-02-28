import gevent
from gevent.monkey import patch_all

from wrappers import asynchronous


patch_all()
from gevent.queue import Queue
import signal
from config import HOST, PASSWORD, PORT, TRANSPORT_ID, DB_FILE
from cystanza.stanza import Probe
from database import initialize_database, get_all_users
import xmpp
from time import time

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
        self.sending = Queue()
        self.dispatcher_gl = None
        gevent.signal(signal.SIGTERM, self.disconnect)
        gevent.signal(signal.SIGINT, self.disconnect)

    def disconnect(self):
        self.client.connection.disconnect()
        exit(1)

    def connect(self):
        self.client.connect(HOST, PORT)
        self.client.auth(TRANSPORT_ID, PASSWORD)

    @staticmethod
    def run_forever():
        while True:
            gevent.sleep(1)

    def start(self):
        initialize_database(DB_FILE)
        self.connect()
        self.receiver_loop()
        self.dispatcher_loop()
        self.probe_users()
        self.process_users()
        s = gevent.spawn(self.run_forever)
        s.join()

    @loop
    def dispatcher_loop(self):
        self.client.process()

    @loop
    def receiver_loop(self):
        self.client.send(self.sending.get())

    def add_user(self, user):
        self.users.update({user.jid: user})

    def send(self, stanza):
        self.sending.put(stanza)

    @asynchronous
    def probe_users(self):
        all_users = get_all_users()
        for user in all_users:
            try:
                jid = user[0]
            except (KeyError, ValueError, IndexError) as e:
                logger.error('%s while sending probes' % e)
                continue
            self.sending.put(Probe(TRANSPORT_ID, jid))

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
