__author__ = 'ernado'

import time
import logging

logger = logging.getLogger("vk4xmpp")
import json

from config import TRANSPORT_FEATURES
from errors import ConnectionError
import user as user_api
import database

import pickle


class Gateway(object):
    def __init__(self):
        self.handlers = []
        self.group_handlers = []
        self.client_list = []
        self.jid_to_id = {}
        self.client_list_length = 0
        self.start_time = int(time.time())
        self.features = TRANSPORT_FEATURES
        self.component = None

    def register_handler(self, name, handler_class):
        self.component.RegisterHandler(name, handler_class(self).handle)

    def register_parser(self, handler):
        self.handlers.append(handler)

    def register_disconnect_handler(self, handler):
        self.component.RegisterDisconnectHandler(handler)

    def process_client(self, jid):
        """
        Updates client messages, friends and status
        @type jid: unicode
        @param jid: client jid
        @return:
        """
        assert isinstance(jid, unicode)

        logger.debug('processing client %s' % jid)

        # checking user status
        if not database.is_user_online(jid):
            logger.debug('user %s offline' % jid)
            database.remove_online_user(jid)
            return

        # checking user time out
        if user_api.is_timed_out(jid):
            logger.debug('timeout for client %s' % jid)
            database.remove_online_user(jid)
            return

        user_api.update_friends(jid)
        user_api.send_messages(jid)


    def add_user(self, jid):

        assert isinstance(jid, unicode)

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

        self.process_client(jid)

    def main_loop_iteration(self):
        now = time.time()
        clients = database.get_clients()
        if not clients:
            logger.debug('no clients')
            return
        l = len(map(self.process_client, clients))
        logger.debug('iterated for %.2f ms - %s users' % ((time.time() - now)*1000, l))

    def send(self, stanza):
        try:
            self.component.send(stanza)
        except KeyboardInterrupt:
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

