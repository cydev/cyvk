import os
from config import DB_FILE
from itypes import Database
from realtime import logger, remove_online_user, r, _users_key, set_roster_flag, set_last_message, set_friends, _get_token_key

__author__ = 'ernado'



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
    remove_online_user(jid)
    with Database(DB_FILE) as db:
        db("DELETE FROM users WHERE jid=?", (jid,))
        db.commit()
        logger.debug('DB: removed %s' % jid)


def get_all_users():
    with Database(DB_FILE) as db:
        return db("SELECT * FROM users").fetchall()


def insert_user(jid, username, token, last_msg_id, roster_set):
    logger.debug('DB: adding user %s' % jid)

    r.sadd(_users_key, jid)
    if roster_set:
        set_roster_flag(jid)
    set_last_message(jid, last_msg_id)
    set_token(jid, token)
    set_friends(jid, {})


    with Database(DB_FILE) as db:
        db("INSERT INTO users VALUES (?,?,?,?,?)", (jid, username,
                                                    token, last_msg_id, roster_set))


def get_description(jid):
    with Database(DB_FILE) as db:
        db("SELECT * FROM users WHERE jid=?", (jid,))
        data =  db.fetchone()
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
    r.set(_get_token_key(user), token)
    with Database(DB_FILE) as db:
        db("UPDATE users SET token=? WHERE jid=?", (token, user))