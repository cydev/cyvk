from __future__ import unicode_literals
from database import get_all_users
from parallel.stanzas import push
from compat import get_logger
from config import TRANSPORT_ID
from cystanza.stanza import Probe

_logger = get_logger()


def probe_users():
    _logger.info('probing users')

    users = get_all_users()
    if not users:
        return _logger.info('no users for probing')

    for user in users:
        try:
            jid = user[0]
        except (KeyError, ValueError, IndexError) as e:
            _logger.error('%s while sending probes' % e)
            continue

        _logger.debug('probing %s' % jid)
        push(Probe(TRANSPORT_ID, jid))