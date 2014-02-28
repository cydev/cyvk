from __future__ import unicode_literals

import time
import logging

import redis

from api.errors import InvalidTokenError, AuthenticationException
from parallel.stanzas import push
from config import TRANSPORT_ID, IDENTIFIER
from database import set_token, get_all_users
from friends import get_friend_jid
from parallel import realtime
from api.vkapi import Api
import database
from cystanza.stanza import SubscribePresence, AvailablePresence, UnavailablePresence, Probe
from config import REDIS_DB, REDIS_CHARSET, REDIS_PREFIX, REDIS_PORT, REDIS_HOST


START_POLLING_KEY = ':'.join([REDIS_PREFIX, 'long_polling_start_queue'])
logger = logging.getLogger("cyvk")


class UserApi(object):
    def __init__(self, jid):
        self.jid = jid
        self.vk = Api(self)

    def roster_subscribe(self, subscriptions=None):
        """Subscribe user for jid in dist"""
        if not subscriptions:
            return push(SubscribePresence(TRANSPORT_ID, self.jid))
        for uid, value in subscriptions.iteritems():
            push(SubscribePresence(get_friend_jid(uid), self.jid, nickname=value["name"]))

    def start_polling(self):
        r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, REDIS_DB, charset=REDIS_CHARSET)
        r.lpush(START_POLLING_KEY, self.jid)

    @property
    def friends(self):
        return realtime.get_friends(self.jid)

    @property
    def friends_online(self):
        friends = self.friends
        return filter(lambda uid: friends[uid]['online'], friends)

    def send_init_presence(self):
        """Sends initial presences to user about friends and transport"""
        logger.debug('user api: sending initial status to %s')
        friends_online = self.friends_online
        for friend_uid in friends_online:
            push(AvailablePresence(get_friend_jid(friend_uid), self.jid, nickname=self.friends[friend_uid]['name']))
        push(AvailablePresence(TRANSPORT_ID, self.jid, nickname=IDENTIFIER['name']))

    def send_out_presence(self, status=None):
        logger.debug("user api: sending out presence for %s" % self.jid)
        notification_list = realtime.get_friends(self.jid).keys() + [TRANSPORT_ID]

        for uid in notification_list:
            push(UnavailablePresence(get_friend_jid(uid), self.jid, status=status))

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
            push(cls(get_friend_jid(uid), jid))

        realtime.set_friends(jid, friends_vk)

    def initialize(self, send=True):
        """Initializes user by subscribing to friends and sending initial presence"""
        jid = self.jid
        logger.debug("user api: called init for user %s" % jid)
        friends = self.vk.get_friends()
        realtime.set_friends(jid, friends)
        self.unset_polling()
        realtime.unset_polling(jid)
        realtime.unset_processing(jid)

        if friends:
            logger.debug("user api: subscribing friends for %s" % jid)
            self.roster_subscribe(friends)
        self.roster_subscribe()  # subscribing to transport

        if send:
            logger.debug('sending initial presence')
            self.send_init_presence()

    def load(self):
        jid = self.jid
        logger.debug("user api: loading %s" % jid)
        desc = database.get_description(jid)

        if not desc:
            raise ValueError('user api: user not found %s' % jid)

        logger.debug("user api: %s exists in db" % jid)
        jid = desc['jid']
        realtime.set_last_message(jid, desc['last_message_id'])
        realtime.set_friends(jid, {})
        logger.debug("user api: %s data loaded" % jid)

    def connect(self, token):
        jid = self.jid
        logger.debug("user api: connecting %s" % jid)

        if not token:
            raise AuthenticationException('no token for %s' % jid)

        try:
            logger.debug('user api: trying to auth with token')
            if not self.vk.is_application_user():
                raise InvalidTokenError('not application user')
            set_token(jid, token)
            logger.debug("user api: authenticated %s" % jid)
        except InvalidTokenError as token_error:
            raise AuthenticationException('invalid token: %s' % token_error)

    def process(self):
        if realtime.is_processing(self.jid):
            return logger.debug('already processing client %s' % self.jid)
        realtime.set_processing(self.jid)
        if not realtime.is_polling(self.jid):
            self.update_friends()
            self.vk.messages.send_messages()
            self.start_polling()
        else:
            logger.debug('updates for %s are handled by polling' % self.jid)
        realtime.unset_processing(self.jid)

    def add(self):
        logger.debug('add_client %s' % self.jid)
        if realtime.is_client(self.jid):
            return logger.debug('%s is already a client' % self.jid)
        realtime.add_online_user(self.jid)
        self.process()

    def set_offline(self):
        realtime.remove_online_user(self.jid)

    def set_online(self):
        realtime.add_online_user(self.jid)

    def set_token(self, token):
        assert isinstance(token, unicode)
        realtime.set_token(self.jid, token)

    @property
    def is_polling(self):
        return realtime.is_polling(self.jid)

    def set_polling(self):
        realtime.set_polling(self.jid)

    def unset_polling(self):
        realtime.unset_polling(self.jid)

    @property
    def token(self):
        return realtime.get_token(self.jid)

    def save(self):
        database.insert_user(self.jid, None, self.token, None, False)

    @property
    def is_client(self):
        return realtime.is_client(self.jid)

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


def probe_users():
    logger.info('probing users')

    users = get_all_users()
    if not users:
        return logger.info('no users for probing')

    for user in users:
        try:
            jid = user[0]
        except (KeyError, ValueError, IndexError) as e:
            logger.error('%s while sending probes' % e)
            continue

        logger.debug('probing %s' % jid)
        push(Probe(TRANSPORT_ID, jid))