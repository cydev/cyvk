from __future__ import unicode_literals
from api.errors import AuthenticationException
from compat import get_logger
from cystanza.stanza import FeatureQuery, BadRequestErrorStanza, NotImplementedErrorStanza
from cystanza.forms import RegistrationFormStanza, RegistrationResult, RegistrationRequest
import database
from config import IDENTIFIER, TRANSPORT_ID
from cystanza.namespaces import NS_DISCO_INFO, NS_DISCO_ITEMS, NS_REGISTER, NS_DELAY, NS_LAST, NS_RECEIPTS

TRANSPORT_FEATURES = (NS_DISCO_ITEMS,
                      NS_DISCO_INFO,
                      NS_RECEIPTS,
                      NS_REGISTER,
                      # NS_GATEWAY,
                      # NS_VERSION,
                      # xmpp.NS_CAPTCHA,
                      # xmpp.NS_STATS,
                      # xmpp.NS_VCARD,
                      NS_DELAY,
                      # NS_PING,
                      NS_LAST)

logger = get_logger()


def registration_form_handler(user, iq):
    """
    :type iq: RegistrationFormStanza
    :param iq:
    :return: :raise AuthenticationException:
    """
    if iq.destination != TRANSPORT_ID:
        return

    jid = iq.get_origin()
    logger.debug('received register form from %s' % jid)
    token = iq.token
    user.token = token

    try:
        token = token.split("#access_token=")[1].split("&")[0].strip()
    except (IndexError, AttributeError):
        logger.debug('access token is probably in raw format')

    if database.get_description(jid):
        return user.transport.send(NotImplementedErrorStanza(iq, 'You are already in database'))

    try:
        if not token:
            raise AuthenticationException('no token')
        user.connect(token)
        user.set_token(token)
        user.initialize()
    except AuthenticationException as e:
        logger.error('user %s connection failed (from iq)' % jid)
        return user.transport.send(BadRequestErrorStanza(iq, 'Incorrect password or access token: %s' % e))

    user.add()
    user.save()
    logger.debug('registration for %s completed' % jid)
    user.transport.send(RegistrationResult(iq))


def registration_request_handler(user, request):
    """:type request: RegistrationRequest"""
    if request.destination != TRANSPORT_ID:
        return

    user.transport.send(RegistrationFormStanza(TRANSPORT_ID, request.origin, query_id=request.stanza_id))


def discovery_request_handler(user, request):
    """:type request: FeatureQuery"""
    if request.destination != TRANSPORT_ID:
        return
    send = user.transport.send
    send(FeatureQuery(TRANSPORT_ID, request.origin, request.stanza_id, IDENTIFIER['name'], TRANSPORT_FEATURES))