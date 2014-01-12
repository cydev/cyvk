import os
import time
from library.writer import Print, wFile

__author__ = 'ernado'

import logging

logger = logging.getLogger("vk4xmpp")


def get_pid(pid):
    current_pid = os.getpid()
    if os.path.exists(pid):
        old_pid = open(pid).read()
        if old_pid:
            logger.info("Killing old transport instance")
            old_pid = int(old_pid)
            if current_pid != old_pid:
                try:
                    os.kill(old_pid, 15)
                    time.sleep(3)
                    os.kill(old_pid, 9)
                except OSError as os_error:
                    logger.debug('OS error %s' % os_error)

                logger.info("%d killed.\n" % old_pid)
    wFile(pid, str(current_pid))