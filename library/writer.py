# /* coding: utf-8 */
# © simpleApps, 2010

import os
import sys
import time
import logging
import traceback

import config

logger = logging.getLogger("vk4xmpp")

fixme_message = lambda msg: Print("\n#! fixme: \"%s\"." % msg)

last_error = None


def wFile(filename, data, mode="w"):
    with open(filename, mode, 0) as file:
        file.write(data)


# def rFile(filename):
#     with open(filename, "r") as file:
#         return file.read()


def dump_crash(name, text=0, is_fixme=True):
    global last_error
    logger.error("writing crashlog %s" % name)
    if is_fixme:
        fixme_message(name)
    try:
        crash_dir = config.CRASH_DIR
        file_path = "%s/%s.txt" % (crash_dir, name)
        if not os.path.exists(crash_dir):
            os.makedirs(crash_dir)
        exception = wException(True)
        if exception not in ("None", last_error):
            timestamp = time.strftime("| %d.%m.%Y (%H:%M:%S) |\n")
            wFile(file_path, timestamp + exception + "\n", "a")
        last_error = exception
    except:
        fixme_message("crashlog")
        wException()


def Print(text, line=True):
    try:
        if line:
            print text
        else:
            sys.stdout.write(text)
            sys.stdout.flush()
    except (IOError, OSError):
        pass


def wException(File=False):
    try:
        exception = traceback.format_exc().strip()
        if not File:
            Print(exception)
        return exception
    except (IOError, OSError):
        pass


def returnExc():
    exc = sys.exc_info()
    if any(exc):
        error = "\n%s: %s " % (exc[0].__name__, exc[1])
    else:
        error = `None`
    return error