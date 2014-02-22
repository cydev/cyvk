import database
from errors import AuthenticationException
from friends import get_friend_jid
from parallel import realtime, sending
from parallel.stanzas import push
from parallel.updates import set_online
from events.toggle import raise_event
from events.constants import USER_ONLINE
from transport import user as user_api, statuses
from config import TRANSPORT_ID
from transport.statuses import get_status_stanza
from transport.presence import PresenceWrapper

import logging

logger = logging.getLogger('vk4xmpp')


def presence_handler_wrapper(h):
    def wrapper(jid, presence):
        assert isinstance(jid, unicode)
        assert isinstance(presence, PresenceWrapper)
        h(jid, presence)

    return wrapper


def _unavailable(jid, presence):
    """
    Unavailable presence handler

    @type presence: PresenceWrapper
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
    xmpp_presence = statuses.get_unavailable_stanza(jid)
    push(xmpp_presence)
    realtime.remove_online_user(jid)


def _error(jid, presence):
    """
    Error presence handler

    @type presence: PresenceWrapper
    @param presence: presence object
    @param jid: client jid
    @raise NotImplementedError:
    """
    logger.debug('error presence %s' % presence)

    if presence.error_code == "404":
        raise NotImplementedError('client_disconnect for %s' % jid)

    raise NotImplementedError('error presence')


def _available(jid, presence):
    """
    Available status handler
    @type presence: PresenceWrapper
    @param presence: Presence object
    @param jid: client jid
    @return:
    """
    if presence.destination_id != TRANSPORT_ID:
        return

    logger.debug("user %s, will send sendInitPresence" % presence.origin_id)
    logger.warning('not adding resource %s to %s' % (presence.resource, jid))


def _unsubscribe(jid, presence):
    """
    Client unsubscribe handler
    @type jid: str
    @type presence: PresenceWrapper
    @param presence: Presence object
    @param jid: client jid
    """

    if realtime.is_client(jid) and presence.destination_id == TRANSPORT_ID:
        database.remove_user(jid)
        logger.debug("user removed registration: %s" % jid)


def _attempt_to_add_client(jid, _):
    """
    Attempt to add client to transport and initialize it
    @type jid: unicode
    @param jid: client jid
    @return:
    """
    logger.debug('presence: attempting to add %s to transport' % jid)

    user = database.get_description(jid)
    if not user:
        logger.debug('presence: user %s not found in database' % jid)
        return
    logger.debug('presence: user %s found in database' % jid)

    token = user['token']

    try:
        user_api.connect(jid, token)
        user_api.initialize(jid, send_precense=True)
        user_api.add_client(jid)
        set_online(jid)
        raise_event(USER_ONLINE)
    except AuthenticationException as e:
        logger.error('unable to authenticate %s: %s' % (jid, e))
        message = "Authentication failed! " \
                  "If this error repeated, please register again. " \
                  "Error: %s" % e
        sending.send(jid, message, TRANSPORT_ID)


def _subscribe(jid, presence):
    """
    Subscribe presence handler

    @type jid: str
    @type presence: PresenceWrapper
    @param presence: presence object
    @param jid: client jid
    @return:
    """
    origin = presence.origin
    destination = presence.destination_id

    if destination == TRANSPORT_ID:
        logger.debug('sending presence about transport <subscribe>')
        push(get_status_stanza(TRANSPORT_ID, origin, status='subscribed'))
        push(get_status_stanza(TRANSPORT_ID, origin))
    else:
        push(get_status_stanza(destination, origin,  status='subscribed'))

        client_friends = realtime.get_friends(jid)
        logger.debug('sending presence about friend <subscribe>')

        if not client_friends:
            return

        friend_id = get_friend_jid(destination)

        if friend_id not in client_friends:
            return

        friend_status = 'unavailable'
        if client_friends[friend_id]['online']:
            friend_status = 'available'

        push(get_status_stanza(destination, origin, status=friend_status))

        # wtf?
        push(get_status_stanza(origin, origin))


_mapping = {'available': _available, 'probe': _available, None: _available,
            'unavailable': _unavailable, 'error': _error, 'subscribe': _subscribe,
            'unsubscribe': _unsubscribe}


def _handle_presence(jid, presence):
    """
    Status update handler for client
    @type presence: PresenceWrapper
    @param presence: status presence
    @param jid: client jid
    """
    status = presence.status
    logger.debug('presence status: %s' % status)
    try:
        presence_handler_wrapper(_mapping[status])(jid, presence)
    except KeyError:
        logger.debug('unable to handle status %s' % status)

    if presence.destination_id == TRANSPORT_ID:
        logger.debug('setting last status %s for %s' % (status, jid))
        realtime.set_last_status(jid, status)


def handler(_, stanza):
    presence = PresenceWrapper(stanza)

    jid = presence.origin_id

    logger.debug('user %s presence handling: %s' % (jid, presence))

    if not isinstance(jid, unicode):
        raise ValueError('jid %s (%s) is not str' % (jid, type(jid)))

    if realtime.is_client(jid):
        _handle_presence(jid, presence)
    elif presence.status in ("available", None):
        _attempt_to_add_client(jid, presence)