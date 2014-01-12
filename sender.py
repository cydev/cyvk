__author__ = 'ernado'

import logging

# from library.writer import dump_crash

logger = logging.getLogger("vk4xmpp")


def stanza_send(cl, stanza):
    if not stanza:
        return

    try:
        logger.debug('sending stanza %s' % stanza)
        cl.send(stanza)
    except KeyboardInterrupt:
        pass
    except IOError:
        logger.error("error while sending stanza %s" % str(stanza))
    except Exception as e:
        logger.critical('crashed while sending stanza: %s' % e)
        raise e
        # dump_crash("Sender")