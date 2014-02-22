import transport.forms

import logging

logger = logging.getLogger("cyvk")


def _send_form(iq, jid):
    logger.debug("sending register form to %s" % jid)
    logger.debug('received: %s' % iq)
    result = transport.forms.get_form_stanza(iq)
    # logger.debug('register form: %s' % result)
    return result