__author__ = 'ernado'

import logging
from config import LOG_FILE, LOG_LEVEL

def get_logger():
    logger = logging.getLogger("vk4xmpp")
    logger.setLevel(LOG_LEVEL)
    h = logging.FileHandler(LOG_FILE)
    f = logging.Formatter("%(asctime)s:%(levelname)s %(message)s",
                                  "[%d.%m.%Y %H:%M:%S]")
    h.setFormatter(f)
    sh = logging.StreamHandler()
    sh.setFormatter(f)
    logger.addHandler(h)
    logger.addHandler(sh)
    return logger