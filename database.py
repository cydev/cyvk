import os
import logging

from config import DB_FILE




#

logger = logging.getLogger("cyvk")

"""
Module "itypes"
itypes.py

Copyright (2010-2013) Al Korgun (alkorgun@gmail.com)

Distributed under the GNU GPLv3.
"""

import sqlite3

connect = sqlite3.connect

__version__ = "0.8"


class Number(object):
    def __init__(self, number=int()):
        self.number = number

    def plus(self, number=0x1):
        self.number += number
        return self.number

    def reduce(self, number=0x1):
        self.number -= number
        return self.number

    __int__ = lambda self: self.number.__int__()

    _int = lambda self: self.__int__()

    __str__ = __repr__ = lambda self: self.number.__repr__()

    _str = lambda self: self.__str__()

    __float__ = lambda self: self.number.__float__()

    __oct__ = lambda self: self.number.__oct__()

    __eq__ = lambda self, number: self.number == number

    __ne__ = lambda self, number: self.number != number

    __gt__ = lambda self, number: self.number > number

    __lt__ = lambda self, number: self.number < number

    __ge__ = lambda self, number: self.number >= number

    __le__ = lambda self, number: self.number <= number


class LazyDescriptor(object):  # not really lazy, but setter is not needed

    def __init__(self, function):
        self.fget = function

    __get__ = lambda self, instance, owner: self.fget(instance)


class Database(object):
    __connected = False

    def __init__(self, filename, lock=None, timeout=8):
        self.filename = filename
        self.lock = lock
        self.timeout = timeout

    def __connect(self):

        assert not self.__connected, "already connected"

        self.db = connect(self.filename, timeout=self.timeout)
        self.cursor = self.db.cursor()
        self.__connected = True
        self.commit = self.db.commit
        self.execute = self.cursor.execute
        self.fetchone = self.cursor.fetchone
        self.fetchall = self.cursor.fetchall
        self.fetchmany = self.cursor.fetchmany

    @LazyDescriptor
    def execute(self):
        self.__connect()
        return self.execute

    __call__ = lambda self, *args: self.execute(*args)

    @LazyDescriptor
    def db(self):
        self.__connect()
        return self.db

    @LazyDescriptor
    def cursor(self):
        self.__connect()
        return self.cursor

    def close(self):

        assert self.__connected, "not connected"

        if self.cursor:
            self.cursor.close()
        if self.db.total_changes:
            self.commit()
        if self.db:
            self.db.close()

    def __enter__(self):
        if self.lock:
            self.lock.acquire()
        return self

    def __exit__(self, *_):
        if self.lock:
            self.lock.release()
        if self.__connected:
            self.close()


del LazyDescriptor


# Stanza processing
def initialize_database(filename):
    logger.info('DB: initializing')
    if not os.path.exists(filename):
        with Database(filename) as db:
            db("CREATE TABLE users (jid TEXT, username TEXT, token TEXT, lastMsgID INTEGER, rosterSet bool)")
            db.commit()
    logger.info('DB: ok')
    return True


def remove_user(jid):
    logger.debug('DB: removing %s' % jid)
    # remove_online_user(jid)
    with Database(DB_FILE) as db:
        db("DELETE FROM users WHERE jid=?", (jid,))
        db.commit()
        logger.debug('DB: removed %s' % jid)


def get_all_users():
    with Database(DB_FILE) as db:
        return db("SELECT * FROM users").fetchall()


def insert_user(jid, username, token, last_msg_id, roster_set):
    logger.debug('DB: adding user %s' % jid)

    with Database(DB_FILE) as db:
        db("INSERT INTO users VALUES (?,?,?,?,?)", (jid, username,
                                                    token, last_msg_id, roster_set))


def get_description(jid):
    with Database(DB_FILE) as db:
        db("SELECT * FROM users WHERE jid=?", (jid,))
        data = db.fetchone()
    try:
        jid, username, token, last_message_id, roster_set_flag = data
    except TypeError:
        return None
    return {
        'jid': jid,
        'username': username,
        'token': token,
        'last_message_id': last_message_id,
        'roster_set_flag': roster_set_flag
    }


def set_token(user, token):
    with Database(DB_FILE) as db:
        db("UPDATE users SET token=? WHERE jid=?", (token, user))


