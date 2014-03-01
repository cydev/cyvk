from __future__ import unicode_literals
from . import updates
from compat import get_logger

_logger = get_logger()


def event_handler(user, data):
    jid = user.jid

    try:
        if not data['updates']:
            _logger.debug('no updates for %s' % jid)

        for update in data['updates']:
            updates.handle_update(user, update)
    except KeyError:
        _logger.error('unable to process %s' % data)

    if not user.is_client:
        return _logger.debug('ending polling for %s' % jid)

    user.start_polling()

