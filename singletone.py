__author__ = 'ernado'

import time
import logging

logger = logging.getLogger("vk4xmpp")

from config import transport_features, SLICE_STEP, ROSTER_TIMEOUT, ACTIVE_TIMEOUT
from run import run_thread
from library.writer import dump_crash
from vk2xmpp import vk2xmpp


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

    def update_transports_list(self, user, add=True):
        if add and user not in self.client_list:
            self.client_list.append(user)
        elif user in self.client_list:
            self.client_list.remove(user)
        length = len(self.client_list)
        if length > self.client_list_length:
            start = self.client_list_length
            self.client_list_length += SLICE_STEP
            end = self.client_list_length
            run_thread(self.hyper_thread, (start, end), "updateTransportsList")
        elif length <= self.client_list_length - SLICE_STEP:
            self.client_list_length -= SLICE_STEP

    def hyper_thread(self, start, end):
        while True:
            current_slice = self.client_list[start:end]
            # if not current_slice:
            #     break
            now = time.time()
            for user in current_slice:
                if not user.vk.is_online:
                    continue

                if not (now - user.last_activity < ACTIVE_TIMEOUT or now - user.last_update > ROSTER_TIMEOUT):
                    continue

                user.last_udate = time.time()
                friends = user.vk.get_friends() # TODO: Update only statuses
                user.vk.method("account.setOnline")
                if friends != user.friends:
                    for uid, value in friends.iteritems():
                        if uid in user.friends:
                            if user.friends[uid]["online"] != value["online"]:
                                user.send_presence(user.jid_from, vk2xmpp(uid),
                                                   None if value["online"] else "unavailable")
                        else:
                            user.roster_subscribe({uid: friends[uid]})
                    user.friends = friends
                user.send_messages()
                del friends
            del current_slice, now
            time.sleep(ROSTER_TIMEOUT)

    def send(self, stanza):
        try:
            self.component.send(stanza)
        except KeyboardInterrupt:
            pass
        except IOError:
            logger.error("Panic: Couldn't send stanza: %s" % str(stanza))
        except Exception as e:
            logger.critical('Crashed: %s' % e)
            dump_crash("Sender")

    def connect(self, server, port):
        logger.info("Connecting")
        r =  self.component.connect((server, port))
        if r:
            logger.info("Connected")
            return True
        else:
            logger.info("Connection failed")
            return False