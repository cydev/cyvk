__author__ = 'ernado'

import time
import logging

logger = logging.getLogger("vk4xmpp")

from config import transport_features, SLICE_STEP, ROSTER_TIMEOUT, ACTIVE_TIMEOUT
from run import run_thread
from library.writer import dump_crash
from errors import ConnectionError
import user as user_api
import database

class Gateway(object):
    def __init__(self):
        self.handlers = []
        self.group_handlers = []
        self.clients = {}
        self.client_list = []
        self.jid_to_id = {}
        self.client_list_length = 0
        self.start_time = int(time.time())
        self.features = transport_features
        self.component = None

    def register_handler(self, name, handler_class):
        self.component.RegisterHandler(name, handler_class(self).handle)

    def register_parser(self, handler):
        self.handlers.append(handler)

    def register_disconnect_handler(self, handler):
        self.component.RegisterDisconnectHandler(handler)

    def process_client(self, jid):
        now = time.time()

        if not database.is_user_online(jid):
            return

        last_activity = database.get_last_activity(jid)
        last_update = database.get_last_update(jid)

        if not (now - last_activity < ACTIVE_TIMEOUT or now - last_update > ROSTER_TIMEOUT):
            return

        user_api.update_last_activity(jid)
        friends_vk = user_api.get_friends(jid)
        friends_db = database.get_friends(jid)
        user_api.set_online(jid)

        logger.debug('Updating friends')

        def process_changes(uid):
            friend = friends_vk[uid]

            if uid not in friends_db:
                logger.debug('User %s not found in friends db' % uid)
                user_api.roster_subscribe(self, jid, {uid: friend})
                return

            if friends_db[uid]['online'] != friend["online"]:
                status = None if friend["online"] else "unavailable"
                user_api.send_presence(self, jid, uid, status)

        if friends_vk != friends_db:
            map(process_changes, friends_vk)

        user_api.send_messages(self, jid)

    def add_user(self, jid):
        logger.debug('add_user %s' % jid)
        is_client = database.is_client(jid)
        if is_client:
           logger.debug('%s already a client' % jid)
           return
        database.add_online_user(jid)
        self.process_client(jid)

    def remove_user(self, jid):
        logger.debug('remove_user %s' % jid)
        is_client = database.is_client(jid)
        if not is_client:
            logger.debug('%s already not in transport')
            return
        database.remove_online_user(jid)
        self.process_client(jid)

    def update_transports_list(self, user, add=True):
        jid = user.jid
        is_client = database.is_client(jid)
        if not is_client:
            if add:
                database.add_online_user(jid)
            else:
                database.remove_online_user(jid)
        length = len(self.client_list)

        if length > self.client_list_length:
            start = self.client_list_length
            self.client_list_length += SLICE_STEP
            end = self.client_list_length
            run_thread(self.hyper_thread, (start, end), "updateTransportsList")
        elif length <= self.client_list_length - SLICE_STEP:
            self.client_list_length -= SLICE_STEP



    def hyper_thread(self):
        while True:
            now = time.time()
            logger.debug('hyper_thread iteration')
            clients = database.get_users()
            map(self.process_client, clients)
            logger.debug('iterated for %s' % (time.time() - now))
            time.sleep(ROSTER_TIMEOUT)

    def send(self, stanza):
        try:
            self.component.send(stanza)
        except KeyboardInterrupt:
            pass
        except IOError as e:
            logger.error("Panic: Couldn't send stanza: %s, %s" % (str(stanza), e))
        except Exception as e:
            # TODO: More accurate exception handling
            logger.critical('Crashed: %s' % e)
            dump_crash("Sender")

    def connect(self, server, port):
        r =  self.component.connect((server, port))
        if r:
            return True
        else:
            raise ConnectionError