from __future__ import unicode_literals
from api.errors import AuthenticationException
from friends import get_friend_jid
from config import TRANSPORT_ID
from cystanza.stanza import Presence, ChatMessage, AvailablePresence, UnavailablePresence
import compat

_logger = compat.get_logger()


def _presence_handler_wrapper(h):
    def wrapper(user, presence):
        assert isinstance(presence, Presence)
        h(user, presence)

    return wrapper


def _unavailable(user, presence):
    """Unavailable presence handler"""
    _logger.debug('unavailable presence %s' % presence)

    if presence.destination != TRANSPORT_ID:
        return
    user.set_offline()


def _error(user, presence):
    _logger.debug('error presence %s' % presence)
    raise NotImplementedError('error presence for %s' % user)


def _available(_, presence):
    if presence.destination != TRANSPORT_ID:
        return

    # user.set_online()
    _logger.debug("user %s, will send sendInitPresence" % presence.origin)
    # _logger.warning('not adding resource for %s' % user.jid)


def _unsubscribe(user, presence):
    if user.is_client and presence.destination == TRANSPORT_ID:
        user.delete()
        _logger.debug("user removed registration: %s" % user.jid)


def _attempt_to_add_client(user, _):
    jid = user.jid
    _logger.debug('presence: attempting to add %s to transport' % jid)

    try:
        user.load()
        user.connect()
        user.initialize()
        user.add()
        user.vk.set_online()
    except AuthenticationException as e:
        _logger.error('unable to authenticate %s: %s' % (jid, e))
        message = "Authentication failed! " \
                  "If this error repeated, please register again. " \
                  "Error: %s" % e
        user.transport.send(ChatMessage(TRANSPORT_ID, jid, message))


def _subscribe(user, presence):
    origin = presence.get_origin()
    destination = presence.get_destination()
    user.transport.sendSubscribedPresence(destination, origin)

    if destination == TRANSPORT_ID:
        return user.transport.send(AvailablePresence(destination, origin))

    friend_id = get_friend_jid(destination)
    client_friends = user.friends or []
    _logger.debug('sending presence about friend <subscribe>')

    if friend_id in client_friends and client_friends[friend_id]['online']:
        return user.transport.send(AvailablePresence(destination, origin))
    user.transport.send(UnavailablePresence(destination, origin))


_mapping = {'available': _available, 'probe': _available, None: _available,
            'unavailable': _unavailable, 'error': _error, 'subscribe': _subscribe,
            'unsubscribe': _unsubscribe}


def _handle_presence(user, presence):
    status = presence.stanza_type
    _logger.debug('presence status: %s' % status)
    try:
        _presence_handler_wrapper(_mapping[status])(user, presence)
    except KeyError:
        _logger.error('unable to handle status %s' % status)


def handler(user, presence):
    """:type presence: Presence"""
    jid = user.jid
    _logger.debug('user %s presence handling: %s' % (jid, presence))
    if user.is_client:
        _handle_presence(user, presence)
    elif presence.stanza_type in ("available", None):
        _attempt_to_add_client(user, presence)