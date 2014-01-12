import os
import redis
from library.itypes import Database

import logging
from config import DB_FILE, TRANSPORT_ID, REDIS_PREFIX, REDIS_HOST, REDIS_PORT, REDIS_DB
import library.xmpp as xmpp



logger = logging.getLogger("vk4xmpp")

def init_db(filename):
    logger.info('Initializing database')
    if not os.path.exists(filename):
        with Database(filename) as db:
            db("CREATE TABLE users (jid TEXT, username TEXT, token TEXT, lastMsgID INTEGER, rosterSet bool)")
            db.commit()
    logger.info('Initialized')
    return True

def remove_user(jid):
    with Database(DB_FILE) as db:
        db("DELETE FROM users WHERE jid=?", (jid,))
        db.commit()

def init_users(gateway):
    logger.info('Initializing users')
    with Database(DB_FILE) as db:
        users = db("SELECT * FROM users").fetchall()

        for user in users:
            logger.debug('user %s initialized' % user[0])
            gateway.send(xmpp.Presence(user[0], "probe", frm=TRANSPORT_ID))

def set_last_message(message_id, jid):
    with Database(DB_FILE) as db:
        db("UPDATE users SET lastMsgID=? WHERE jid=?", (message_id, jid))


def roster_subscribe(roster_set, jid):
    with Database(DB_FILE) as db:
        db("UPDATE users SET rosterSet=? WHERE jid=?", (roster_set, jid))

r = redis.StrictRedis(REDIS_HOST, REDIS_PORT, )

USER_PREFIX = 'user'
TOKEN_PREFIX = 'token'


def get_description(jid):
    with Database(DB_FILE) as db:
        db("SELECT * FROM users WHERE jid=?", (jid,))
        return db.fetchone()


def _get_token_key(user):
    return ':'.join([REDIS_PREFIX, USER_PREFIX, user, TOKEN_PREFIX])

def set_token(user, token):
    r.set(_get_token_key(user), token)

def get_token(user):
    return r.get(_get_token_key(user))