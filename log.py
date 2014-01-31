__author__ = 'ernado'

import logging
from config import LOG_FILE, LOG_LEVEL

def get_logger():
    logger = logging.getLogger("cyvk")
    logger.setLevel(LOG_LEVEL)
    h = logging.FileHandler(LOG_FILE)
    try:
        import colorlog
        f = colorlog.ColoredFormatter('%(yellow)s%(name)-8s %(log_color)s%(message)s', log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red',
        })

        fx = colorlog.ColoredFormatter('%(green)s%(name)-8s %(log_color)s%(message)s', log_colors={
                'DEBUG':    'cyan',
                'INFO':     'yellow',
                'WARNING':  'cyan',
                'ERROR':    'red',
                'CRITICAL': 'red',
        })
    except ImportError:
        f = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s %(message)s")
        fx = logging.Formatter("%(asctime)s:%(levelname)s:%(name)s %(message)s")

    h.setFormatter(f)
    sh = logging.StreamHandler()
    sh.setFormatter(f)
    logger.addHandler(h)
    logger.addHandler(sh)

    sh2 = logging.StreamHandler()
    sh2.setFormatter(fx)
    logger2 = logging.getLogger("xmpp")
    logger2.setLevel('DEBUG')
    logger2.addHandler(sh2)

    return logger