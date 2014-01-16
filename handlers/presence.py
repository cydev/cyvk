# coding: utf-8

from __future__ import unicode_literals

import logging

from config import TRANSPORT_ID
from friends import get_friend_jid
import messaging
from realtime import queue_stanza
import xmpp as xmpp
import database
import realtime
import user as user_api
from handler import Handler
from errors import AuthenticationException


logger = logging.getLogger("vk4xmpp")


class Presence(object):
    def __init__(self, presence):
        self.origin = presence.getFrom()
        self.destination = presence.getTo()
        self.destination_id = self.destination.getStripped()
        self.resource = self.origin.getResource()
        self.origin_id = self.origin.getStripped()
        self.error_code = presence.getErrorCode()
        self.status = presence.getType()
        self.dict = {'origin': self.origin_id, 'destination': self.destination_id,
                     'resource': str(self.resource), 'error_code': str(self.error_code),
                     'status': str(self.status)}

    def __str__(self):
        return '<Presence %s -> %s [%s]>' % (self.origin_id, self.destination_id, self.dict)


def presence_handler_wrapper(handler):

    def wrapper(presence, jid):
        assert isinstance(jid, unicode)
        assert isinstance(presence, Presence)
        handler(presence, jid)

    return wrapper

@presence_handler_wrapper
def _error(presence, jid):
    """
    Error presence handler

    @type presence: Presence
    @param presence: presence object
    @param jid: client jid
    @raise NotImplementedError:
    """
    logger.debug('error presence %s' % presence)

    if presence.error_code == "404":
        raise NotImplementedError('client_disconnect for %s' % jid)

    raise NotImplementedError('error presence')
        # client.vk.disconnect()

@presence_handler_wrapper
def _unavailable(presence, jid):
    """
    Unavailable presence handler

    @type presence: Presence
    @type jid: str
    @param presence: Presence object
    @param jid: client jid
    @return: @raise NotImplementedError:
    """
    logger.debug('unavailable presence %s' % presence)

    # if p.to_s == TRANSPORT_ID and p.resource in client.resources:
    if presence.destination_id != TRANSPORT_ID:
        return

    logger.warning('unavailable presence may be not implemented')
    user_api.send_out_presence(jid)
    queue_stanza(xmpp.Presence(jid, "unavailable", frm=TRANSPORT_ID))
    database.remove_online_user(jid)


@presence_handler_wrapper
def _subscribe(presence, jid):
    """
    Subscribe presence handler

    @type jid: str
    @type presence: Presence
    @param presence: presence object
    @param jid: client jid
    @return:
    """
    if presence.destination_id == TRANSPORT_ID:
        queue_stanza(xmpp.Presence(presence.origin, "subscribed", frm=TRANSPORT_ID))
        queue_stanza(xmpp.Presence(presence.origin, frm=TRANSPORT_ID))
    else:
        queue_stanza(xmpp.Presence(presence.origin, "subscribed", frm=presence.destination_id))

        client_friends = realtime.get_friends(jid)

        if not client_friends:
            return
            # if not client.friends:
        #     return

        friend_id = get_friend_jid(presence.destination_id)

        if friend_id not in client_friends:
            return

        if client_friends[friend_id]['online']:
            return

        queue_stanza(xmpp.Presence(presence.origin, frm=presence.origin))


@presence_handler_wrapper
def _available(presence, jid):
    """
    Available status handler
    @type presence: Presence
    @param presence: Presence object
    @param jid: client jid
    @return:
    """
    if presence.destination_id != TRANSPORT_ID:
        return

    logger.debug("user %s, will send sendInitPresence" % presence.origin_id)
    # client.resources.append(p.resource)
    logger.warning('not adding resource %s to %s' % (presence.resource, jid))
    realtime.set_online(jid)
    # if client.last_status == "unavailable" and len(client.resources) == 1:
    #     if not client.vk.Online:
    #         client.vk.is_online = True
    # if not database.is_user_online(jid):
    #     database.set_online(jid)
    # jid.send_init_presence()


@presence_handler_wrapper
def _unsubscribe(presence, jid):
    """
    Client unsubscribe handler
    @type jid: str
    @type presence: Presence
    @param presence: Presence object
    @param jid: client jid
    """

    if realtime.is_client(jid) and presence.destination_id == TRANSPORT_ID:
        database.remove_user(jid)
        messaging.send_to_watcher("user removed registration: %s" % jid)


@presence_handler_wrapper
def _attempt_to_add_client(_, jid):
    logger.debug("presence: attempting to add %s to transport" % jid)

    user = database.get_description(jid)
    if not user:
        logger.debug('presence: user %s not found in database' % jid)
        return
    logger.debug("presence: user %s found in database" % jid)

    token = user['token']

    try:
        user_api.connect(jid, token)
        user_api.initialize(jid, send=True)
        user_api.make_client(jid)
        user_api.set_online(jid)
    except AuthenticationException as e:
        logger.error('unable to authenticate %s: %s' % (jid, e))
        message = "Authentication failed! " \
                  "If this error repeated, please register again. " \
                  "Error: %s" % e
        messaging.send(jid, message, TRANSPORT_ID)

@presence_handler_wrapper
def _update_client_status(presence, jid):
    """
    Status update handler for client
    @type presence: Presence
    @param presence: status prescense
    @param jid: client jid
    """
    status = presence.status

    mapping = {'available': _available, 'probe': _available, None: _available,
         'unavailable': _unavailable, 'error': _error, 'subscribed': _subscribe,
         'unsubscribe': _unsubscribe
    }

    mapping[status](presence, jid)

    if presence.destination_id == TRANSPORT_ID:
        logger.debug('setting last status %s for %s' % (status, jid))
        realtime.set_last_status(jid, status)

class PresenceHandler(Handler):
    """
    Handler for presence messages from jabber server
    """

    def handle(self, _, stanza):
        presence = Presence(stanza)
        logger.debug('presence handling: %s' % presence)
        jid = presence.origin_id

        if not isinstance(jid, unicode):
            raise ValueError('jid %s (%s) is not str' % (jid, type(jid)))

        if realtime.is_client(jid):
            _update_client_status(presence, jid)
        elif presence.status in ("available", None):
            _attempt_to_add_client(presence, jid)

def get_handler():
    return PresenceHandler().handle