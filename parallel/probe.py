from database import get_all_users
from parallel.stanzas import push
from statuses import get_probe_stanza
from compat import get_logger

_logger = get_logger()


def probe_users():
    _logger.info('probing users')

    users = get_all_users()

    if not users:
        return _logger.info('no users for probing')

    for user in users:
        jid = user[0]
        _logger.debug('probing %s' % jid)
        push(get_probe_stanza(jid))