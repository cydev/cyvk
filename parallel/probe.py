import logging

from database import get_all_users
from parallel.stanzas import push
from transport.statuses import get_probe_stanza

__author__ = 'ernado'

logger = logging.getLogger("cyvk")


def probe_users():
    logger.info('probing users')

    users = get_all_users()

    for user in users:
        jid = user[0]
        logger.debug('probing %s' % jid)
        push(get_probe_stanza(jid))