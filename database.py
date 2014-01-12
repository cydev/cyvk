import os
from library.itypes import Database

__author__ = 'ernado'

import logging
from config import DB_FILE, TRANSPORT_ID
import library.xmpp as xmpp

logger = logging.getLogger("vk4xmpp")

def init_db(filename):
    if not os.path.exists(filename):
        with Database(filename) as db:
            db("CREATE TABLE users (jid TEXT, username TEXT, token TEXT, lastMsgID INTEGER, rosterSet bool)")
            db.commit()
    return True

def init_users(gateway):
    logger.info('Initializing users')
    with Database(DB_FILE) as db:
        users = db("SELECT * FROM users").fetchall()

        for user in users:
            logger.debug('user %s initialized' % user[0])
            gateway.send(xmpp.Presence(user[0], "probe", frm=TRANSPORT_ID))