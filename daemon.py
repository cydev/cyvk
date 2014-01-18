import os
import time

__author__ = 'ernado'

import logging

logger = logging.getLogger("cyvk")


def get_pid(pid):
    current_pid = os.getpid()
    if os.path.exists(pid):
        old_pid = open(pid).read()
        if old_pid:
            logger.info("killing old transport instance")
            old_pid = int(old_pid)
            if current_pid != old_pid:
                try:
                    os.kill(old_pid, 15)
                    time.sleep(3)
                    os.kill(old_pid, 9)
                except OSError as os_error:
                    logger.debug('OS error %s' % os_error)

                logger.info("%d killed" % old_pid)
    # dump_to_file(pid, str(current_pid))
    logger.warning('already exists')