from __future__ import unicode_literals

import time
import logging

from api.errors import InvalidTokenError, AuthenticationException
from parallel.stanzas import push
from parallel.updates import send_messages, get_friends
from config import TRANSPORT_ID, IDENTIFIER
from database import set_token, get_all_users
from friends import get_friend_jid
from parallel import realtime
from parallel.long_polling import start_polling
from api.vkapi import Api
import database
from cystanza.stanza import SubscribePresence, AvailablePresence, UnavailablePresence, Probe


logger = logging.getLogger("cyvk")


class UserApi(object):
    def __init__(self, jid):
        self.jid = jid

    def roster_subscribe(self, subscriptions=None):
        """Subscribe user for jid in dist"""
        if not subscriptions:
            return push(SubscribePresence(TRANSPORT_ID, self.jid))
        for uid, value in subscriptions.iteritems():
            push(SubscribePresence(get_friend_jid(uid), self.jid, nickname=value["name"]))

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
        friends_vk = get_friends(jid)
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
        friends = get_friends(jid)
        realtime.set_friends(jid, friends)
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
        if desc['roster_set_flag']:
            realtime.set_roster_flag(jid)
        realtime.set_friends(jid, {})
        logger.debug("user api: %s data loaded" % jid)

    def connect(self, token):
        jid = self.jid
        logger.debug("user api: connecting %s" % jid)

        if not token:
            raise AuthenticationException('no token for %s' % jid)

        # logger.debug("user api: vk api initialized")
        api = Api(jid, token)
        try:
            logger.debug('user api: trying to auth with token')
            if not api.is_application_user():
                raise InvalidTokenError('not application user')
            set_token(jid, token)
            logger.debug("user api: authenticated %s" % jid)
        # except CaptchaNeeded:
        #     logger.debug("user api: captcha needed for %s" % jid)
        #     raise AuthenticationException('Captcha')
        except InvalidTokenError as token_error:
            raise AuthenticationException('invalid token: %s' % token_error)

        if realtime.is_user(jid):
            logger.debug("user api: updating db for %s" % jid)
            realtime.set_last_activity_now(jid)

    def process(self):
        if realtime.is_processing(self.jid):
            return logger.debug('already processing client %s' % self.jid)
        realtime.set_processing(self.jid)
        if not realtime.is_polling(self.jid):
            self.update_friends()
            send_messages(self.jid)
            start_polling(self.jid)
        else:
            logger.debug('updates for %s are handled by polling' % self.jid)
        realtime.unset_processing(self.jid)

    def add(self):
        logger.debug('add_client %s' % self.jid)
        if realtime.is_client(self.jid):
            return logger.debug('%s is already a client' % self.jid)
        realtime.add_online_user(self.jid)
        self.process()


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