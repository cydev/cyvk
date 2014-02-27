from __future__ import unicode_literals
from api.errors import AuthenticationException
import database
from friends import get_friend_jid
from parallel import realtime
from parallel.stanzas import push
from parallel.updates import set_online
from config import TRANSPORT_ID
from cystanza.stanza import Presence, ChatMessage, AvailablePresence, SubscribedPresence
import compat
import user as user_api

_logger = compat.get_logger()


def _presence_handler_wrapper(h):
    def wrapper(jid, presence):
        assert isinstance(jid, unicode)
        assert isinstance(presence, Presence)
        h(jid, presence)

    return wrapper


def _unavailable(jid, presence):
    """
    Unavailable presence handler

    @type presence: Presence
    @type jid: str
    @param presence: Presence object
    @param jid: client jid
    @return: @raise NotImplementedError:
    """
    _logger.debug('unavailable presence %s' % presence)

    if presence.destination != TRANSPORT_ID:
        return

    realtime.remove_online_user(jid)


def _error(jid, presence):
    """
    Error presence handler

    @type presence: PresenceWrapper
    @param presence: presence object
    @param jid: client jid
    @raise NotImplementedError:
    """
    _logger.debug('error presence %s' % presence)

    if presence.error_code == "404":
        raise NotImplementedError('client_disconnect for %s' % jid)

    raise NotImplementedError('error presence')


def _available(jid, presence):
    """
    Available status handler
    @type presence: Presence
    @param presence: Presence object
    @param jid: client jid
    @return:
    """
    if presence.destination != TRANSPORT_ID:
        return

    _logger.debug("user %s, will send sendInitPresence" % presence.origin)
    _logger.warning('not adding resource for %s' % jid)


def _unsubscribe(jid, presence):
    """
    Client unsubscribe handler
    @type jid: str
    @type presence: Presence
    @param presence: Presence object
    @param jid: client jid
    """

    if realtime.is_client(jid) and presence.destination == TRANSPORT_ID:
        database.remove_user(jid)
        _logger.debug("user removed registration: %s" % jid)


def _attempt_to_add_client(jid, _):
    """
    Attempt to add client to transport and initialize it
    @type jid: unicode
    @param jid: client jid
    @return:
    """
    _logger.debug('presence: attempting to add %s to transport' % jid)

    user = database.get_description(jid)
    if not user:
        _logger.debug('presence: user %s not found in database' % jid)
        return
    _logger.debug('presence: user %s found in database' % jid)

    token = user['token']

    try:
        user_api.connect(jid, token)
        user_api.initialize(jid, send=True)
        user_api.add_client(jid)
        set_online(jid)
    except AuthenticationException as e:
        _logger.error('unable to authenticate %s: %s' % (jid, e))
        message = "Authentication failed! " \
                  "If this error repeated, please register again. " \
                  "Error: %s" % e
        push(ChatMessage(TRANSPORT_ID, jid, message))


def _subscribe(jid, presence):
    """
    Subscribe presence handler

    @type jid: str
    @type presence: Presence
    @param presence: presence object
    @param jid: client jid
    @return:
    """
    origin = presence.get_origin()
    destination = presence.get_destination()
    push(SubscribedPresence(destination, origin))

    if destination == TRANSPORT_ID:
        return push(AvailablePresence(destination, origin))

    friend_id = get_friend_jid(destination)
    client_friends = realtime.get_friends(jid) or []
    _logger.debug('sending presence about friend <subscribe>')

    if friend_id in client_friends and client_friends[friend_id]['online']:
        push(AvailablePresence(destination, origin))


_mapping = {'available': _available, 'probe': _available, None: _available,
            'unavailable': _unavailable, 'error': _error, 'subscribe': _subscribe,
            'unsubscribe': _unsubscribe}


def _handle_presence(jid, presence):
    """
    Status update handler for client
    @type presence: Presence
    @param presence: status presence
    @param jid: client jid
    """
    status = presence.status
    _logger.debug('presence status: %s' % status)
    try:
        _presence_handler_wrapper(_mapping[status])(jid, presence)
    except KeyError:
        _logger.error('unable to handle status %s' % status)

    if presence.destination == TRANSPORT_ID:
        _logger.debug('setting last status %s for %s' % (status, jid))
        realtime.set_last_status(jid, status)


def handler(presence):
    """

    :type presence: Presence
    """
    jid = presence.get_origin()

    _logger.debug('user %s presence handling: %s' % (jid, presence))

    if not isinstance(jid, unicode):
        raise ValueError('jid %s (%s) is not str' % (jid, type(jid)))

    if realtime.is_client(jid):
        _handle_presence(jid, presence)
    elif presence.status in ("available", None):
        _attempt_to_add_client(jid, presence)