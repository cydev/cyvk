from __future__ import unicode_literals

import time
import logging

import requests
import ujson as json

from api.errors import InvalidTokenError, AuthenticationException
from config import TRANSPORT_ID, IDENTIFIER
from database import set_token, get_all_users
from friends import get_friend_jid
from parallel import realtime
from api.vkapi import Api
import database
from cystanza.stanza import SubscribePresence, AvailablePresence, UnavailablePresence, Probe
from parallel.long_polling import event_handler as update_handler
from config import REDIS_DB, REDIS_CHARSET, REDIS_PREFIX, REDIS_PORT, REDIS_HOST, POLLING_WAIT
from wrappers import asynchronous


START_POLLING_KEY = ':'.join([REDIS_PREFIX, 'long_polling_start_queue'])
logger = logging.getLogger("cyvk")


class UserApi(object):
    def __init__(self, transport, jid):
        self.jid = jid
        self.transport = transport
        self.friends = []
        self.processing = False
        self.polling = False
        self.token = None
        self.vk = Api(self)

    def roster_subscribe(self, subscriptions=None):
        """Subscribe user for jid in dist"""
        if not subscriptions:
            return self.transport.send(SubscribePresence(TRANSPORT_ID, self.jid))
        for uid, value in subscriptions.iteritems():
            self.transport.send(SubscribePresence(get_friend_jid(uid), self.jid, nickname=value["name"]))

    @asynchronous
    def start_polling(self):
        if self.polling:
            return logger.debug('already polling %s' % self)
        self.polling = True
        args = self.vk.messages.get_lp_server()
        args['wait'] = 6
        url = 'http://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode=2'.format(**args)
        data = json.loads(requests.get(url).text)
        self.polling = False
        update_handler(self, data)

    @asynchronous
    def handle_updates(self, data):
        update_handler(self, data)

    @property
    def friends_online(self):
        return filter(lambda uid: self.friends[uid]['online'], self.friends)

    def send_init_presence(self):
        """Sends initial presences to user about friends and transport"""
        logger.debug('user api: sending initial status to %s')
        friends_online = self.friends_online
        for friend_uid in friends_online:
            self.transport.send(
                AvailablePresence(get_friend_jid(friend_uid), self.jid, nickname=self.friends[friend_uid]['name']))
        self.transport.send(AvailablePresence(TRANSPORT_ID, self.jid, nickname=IDENTIFIER['name']))

    @asynchronous
    def send_out_presence(self, status=None):
        logger.debug("user api: sending out presence for %s" % self.jid)
        notification_list = realtime.get_friends(self.jid).keys() + [TRANSPORT_ID]

        for uid in notification_list:
            self.transport.send(UnavailablePresence(get_friend_jid(uid), self.jid, status=status))

    def delete(self):
        raise NotImplementedError('deleting users')

    def update_friends(self):
        jid = self.jid
        friends_vk = self.vk.get_friends()
        friends_db = realtime.get_friends(jid)

        if friends_db == friends_vk:
            logger.debug('no changes in friend list for %s' % jid)
            return

        logger.debug('updating friend list for %s' % jid)

        subscriptions = {}
        update_status_dict = {}

        for uid in friends_vk:
            friend = friends_vk[uid]

            if uid not in friends_db:
                logger.debug('friend %s not found' % uid)
                subscriptions.update({uid: friend})
                continue

            if friends_db[uid]['online'] != friend['online']:
                logger.debug('friend %s status changed' % uid)
                status = None if friend["online"] else "unavailable"
                update_status_dict.update({uid: status})

        self.roster_subscribe(subscriptions)

        for uid, status in update_status_dict.items():
            cls = AvailablePresence
            if status:
                cls = UnavailablePresence
            self.transport.send(cls(get_friend_jid(uid), jid))

        realtime.set_friends(jid, friends_vk)

    def initialize(self, send=True):
        """Initializes user by subscribing to friends and sending initial presence"""
        logger.debug("user api: called init for user %s" % self)
        self.friends = self.vk.get_friends()

        if self.friends:
            logger.debug("user api: subscribing friends for %s" % self)
            self.roster_subscribe(self.friends)
        self.roster_subscribe()  # subscribing to transport

        if send:
            logger.debug('sending initial presence')
            self.send_init_presence()

    def load(self):
        logger.debug("user api: loading %s" % self)
        desc = database.get_description(self.jid)

        if not desc:
            raise ValueError('user api: user not found %s' % self)

        logger.debug("user api: %s exists in db" % self)
        self.vk.last_message_id = desc['last_message_id']
        self.token = realtime.get_token(self.jid)
        logger.debug("user api: %s data loaded" % self)

    def connect(self, token=None):
        logger.debug("user api: connecting %s" % self)

        token = token or self.token
        if not token:
            raise AuthenticationException('no token for %s' % self)

        try:
            logger.debug('user api: trying to auth with token')
            if not self.vk.is_application_user():
                raise InvalidTokenError('not application user')
            self.token = token
            logger.debug("user api: authenticated %s" % self)
        except InvalidTokenError as token_error:
            raise AuthenticationException('invalid token: %s' % token_error)

    def process(self):
        if not self.polling:
            self.update_friends()
            self.vk.messages.send_messages()
            self.start_polling()
        else:
            logger.debug('updates for %s are handled by polling' % self.jid)

    def add(self):
        logger.debug('add_client %s' % self.jid)
        if self.jid in self.transport.users:
            return logger.debug('%s is already a client' % self.jid)
        self.transport.users.update({self.jid: self})
        self.process()

    def set_offline(self):
        del self.transport.users[self.jid]

    def set_online(self):
        self.transport.users.update({self.jid: self})

    def set_token(self, token):
        self.token = token
        self.save()

    @property
    def is_polling(self):
        return realtime.is_polling(self.jid)

    def set_polling(self):
        realtime.set_polling(self.jid)

    def unset_polling(self):
        realtime.unset_polling(self.jid)

    def save(self):
        database.insert_user(self.jid, None, self.token, None, False)

    @property
    def is_client(self):
        return self.jid in self.transport.users

    def __str__(self):
        return str(self.jid)


def delete_user(jid):
    assert isinstance(jid, unicode)

    logger.debug("user api: delete_user %s" % jid)

    # friends = realtime.get_friends(jid)
    raise NotImplementedError('deleting users')
    # for friend_id in friends:
    #
    #     friend_jid = get_friend_jid(friend_id)
    #
    #     send_presence(jid, friend_jid, "unsubscribe")
    #     send_presence(jid, friend_jid, "unsubscribed")
    #
    # database.remove_user(jid)
    # realtime.remove_online_user(jid)


def process_users():
    now = time.time()
    clients = realtime.get_clients()

    if not clients:
        logger.debug('no clients')
        return

    for client in clients:
        user = UserApi(client)
        user.process()

    logger.debug('iterated for %.2f ms' % ((time.time() - now) * 1000))


