from __future__ import unicode_literals
from api.errors import AuthenticationException
import database
from friends import get_friend_jid
from parallel.stanzas import push
from config import TRANSPORT_ID
from cystanza.stanza import Presence, ChatMessage, AvailablePresence, SubscribedPresence, UnavailablePresence
import compat
from user import UserApi

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


def _available(user, presence):
    if presence.destination != TRANSPORT_ID:
        return

    _logger.debug("user %s, will send sendInitPresence" % presence.origin)
    _logger.warning('not adding resource for %s' % user.jid)


def _unsubscribe(user, presence):
    if user.is_client and presence.destination == TRANSPORT_ID:
        user.delete()
        _logger.debug("user removed registration: %s" % user.jid)


def _attempt_to_add_client(user, _):
    jid = user.jid
    _logger.debug('presence: attempting to add %s to transport' % jid)

    description = database.get_description(jid)
    if not description:
        _logger.debug('presence: user %s not found in database' % jid)
        return
    _logger.debug('presence: user %s found in database' % jid)

    token = description['token']

    try:
        user.connect(token)
        user.initialize()
        user.add()
        user.vk.set_online()
    except AuthenticationException as e:
        _logger.error('unable to authenticate %s: %s' % (jid, e))
        message = "Authentication failed! " \
                  "If this error repeated, please register again. " \
                  "Error: %s" % e
        push(ChatMessage(TRANSPORT_ID, jid, message))


def _subscribe(user, presence):
    origin = presence.get_origin()
    destination = presence.get_destination()
    push(SubscribedPresence(destination, origin))

    if destination == TRANSPORT_ID:
        return push(AvailablePresence(destination, origin))

    friend_id = get_friend_jid(destination)
    client_friends = user.friends or []
    _logger.debug('sending presence about friend <subscribe>')

    if friend_id in client_friends and client_friends[friend_id]['online']:
        return push(AvailablePresence(destination, origin))
    push(UnavailablePresence(destination, origin))


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


def handler(presence):
    """:type presence: Presence"""
    jid = presence.get_origin()

    _logger.debug('user %s presence handling: %s' % (jid, presence))

    if not isinstance(jid, unicode):
        raise ValueError('jid %s (%s) is not str' % (jid, type(jid)))
    user = UserApi(jid)
    if user.is_client:
        _handle_presence(user, presence)
    elif presence.status in ("available", None):
        _attempt_to_add_client(user, presence)