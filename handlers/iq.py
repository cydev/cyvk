import transport.forms
from compat import get_logger

_logger = get_logger()


def _send_form(iq, jid):
    _logger.debug("sending register form to %s" % jid)
    _logger.debug('received: %s' % iq)
    result = transport.forms.get_form_stanza(iq)
    return result