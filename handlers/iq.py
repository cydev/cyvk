from __future__ import unicode_literals
from errors import AuthenticationException
from compat import get_logger
from cystanza.stanza import FeatureQuery, BadRequestErrorStanza, NotImplementedErrorStanza
from cystanza.forms import RegistrationFormStanza, RegistrationResult, RegistrationRequest
import database
import user as user_api
from parallel import realtime
from parallel.stanzas import push
from config import IDENTIFIER, TRANSPORT_ID
from features import TRANSPORT_FEATURES

logger = get_logger()


def registration_form_handler(iq):
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

    try:
        token = token.split("#access_token=")[1].split("&")[0].strip()
    except (IndexError, AttributeError):
        logger.debug('access token is probably in raw format')

    if database.get_description(jid):
        return push(NotImplementedErrorStanza(iq, 'You are already in database'))

    try:
        if not token:
            raise AuthenticationException('no token')
        user_api.connect(jid, token)
        realtime.set_token(jid, token)
        user_api.initialize(jid)
    except AuthenticationException as e:
        logger.error('user %s connection failed (from iq)' % jid)
        return push(BadRequestErrorStanza(iq, 'Incorrect password or access token: %s' % e))

    realtime.set_last_activity_now(jid)
    user_api.add_client(jid)
    database.insert_user(jid, None, token, None, False)
    logger.debug('registration for %s completed' % jid)
    push(RegistrationResult(iq))


def registration_request_handler(request):
    """
    :type request: RegistrationRequest
    """
    if request.destination != TRANSPORT_ID:
        return

    push(RegistrationFormStanza(TRANSPORT_ID, request.origin, query_id=request.stanza_id))


def discovery_request_handler(request):
    """
    :type request: FeatureQuery
    """
    if request.destination != TRANSPORT_ID:
        return

    push(FeatureQuery(TRANSPORT_ID, request.origin, request.stanza_id, IDENTIFIER['name'], TRANSPORT_FEATURES))