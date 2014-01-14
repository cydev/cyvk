__author__ = 'ernado'

import time
import logging

logger = logging.getLogger("vk4xmpp")

from config import transport_features, SLICE_STEP, ROSTER_TIMEOUT, ACTIVE_TIMEOUT
from errors import ConnectionError
import user as user_api
import database


class Gateway(object):
    def __init__(self):
        self.handlers = []
        self.group_handlers = []
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
        logger.debug('processing client %s' % jid)

        if not database.is_user_online(jid):
            logger.debug('user %s offline' % jid)
            return

        if user_api.is_timed_out(jid):
            logger.debug('timeout for client %s' % jid)
            database.remove_online_user(jid)
            return

        # user_api.update_last_activity(jid)
        # user_api.set_online(jid)
        user_api.update_friends(self, jid)
        user_api.send_messages(self, jid)


    def add_user(self, jid):
        logger.debug('add_user %s' % jid)
        if database.is_client(jid):
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
        # length = len(self.client_list)

        self.process_client(jid)

        # if length > self.client_list_length:
        #     start = self.client_list_length
        #     self.client_list_length += SLICE_STEP
        #     end = self.client_list_length
        #     run_thread(self.main_loop, (start, end), "updateTransportsList")
        # elif length <= self.client_list_length - SLICE_STEP:
        #     self.client_list_length -= SLICE_STEP



    def main_loop(self):
        while True:
            now = time.time()
            # logger.debug('hyper_thread iteration')
            clients = database.get_users()
            l = len(map(self.process_client, clients))
            logger.debug('iterated for %.2f ms - %s users' % ((time.time() - now)*1000, l))
            time.sleep(7)

    def send(self, stanza):
        try:
            self.component.send(stanza)
        except KeyboardInterrupt:
            pass
            logger.debug('ignoring KeyboardInterrupt')
        except IOError as e:
            logger.error("couldn't send stanza: %s, %s" % (str(stanza), e))
        # except Exception as e:
        #     # TODO: More accurate exception handling
        #     logger.critical('Crashed: %s' % e)
        #     dump_crash("Sender")

    def connect(self, server, port):
        r =  self.component.connect((server, port))
        if r:
            return True
        else:
            raise ConnectionError