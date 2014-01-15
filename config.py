# coding: utf

import library.xmpp as xmpp
import logging

# connection host.
# for Prosody "vk.example.com"
HOST = "s1.cydev"

# connection server (usually equals host)
# for Prosody "example.com"
SERVER = "vk.s1.cydev"

# connection port (as you set in your jabber-server config)
# default for Prosody is 5347
PORT = 5556

# transport ID
TRANSPORT_ID = "vk.s1.cydev"

# connection password.
PASSWORD = "secret"

# default status (1 - online / 0 - offline)
DEFAULT_STATUS = 1

# save last message id (recommended)
USE_LAST_MESSAGE_ID = True

# avatar photo size (photo_50, photo_100, photo_200_orig)
PHOTO_SIZE = "photo_100"

# white list
# if set, only users from listed servers are allowed to access transport
# for example WHITE_LIST = ['xmppserver1.ru, 'xmppserver2.com']
WHITE_LIST = []

# users with jid from this list are receiving registration notifications
# WATCHER_LIST = [] for no notifications
WATCHER_LIST = ['ernado@vk.s1.cydev']

# addition description text for transport vcard
ADDITIONAL_ABOUT = ""

# F.e. conference.example.com
# conference server
# WARNING: feature is in alpha testing
# CONFERENCE_SERVER = '' for no group chats
CONFERENCE_SERVER = ''

# user registration limit
# USER_LIMIT = 0 for unlimited registration
USER_LIMIT = 0

# Danger zone.
# DANGER ZONE
# edit settings below if you are definitely know what you are doing

# timeout when user considered inactive (seconds)
# default 600
ACTIVE_TIMEOUT = 600

# roster update rate in seconds for inactive users
# default 180
ROSTER_TIMEOUT = 180

# roster update rate in seconds for active users
# default 6
ROSTER_UPDATE_TIMEOUT = 6

# maximum forwarded messages depth
MAXIMUM_FORWARD_DEPTH = 5

LOGO_URL = 'https://raw.github.com/cydev/cyvk/master/logo.png'

# image replace for avatars
URL_VCARD_NO_IMAGE = LOGO_URL

# debug mode for xmppy library
DEBUG_XMPPPY = False

# sqlite database filename
DB_FILE = "users.db"

# pid file
PID_FILE = "pidFile.txt"

# log file
LOG_FILE = "vk4xmpp.log"

IDENTIFIER = {"type": "vk",
                "category": "gateway",
                "name": "cyvk transport"}

BANNED_CHARS = [unichr(x) for x in xrange(32) if x not in (9, 10, 13)] + [unichr(57003)]

LOCALE = 'ru'

LOCALE_PATH = 'locales'

DESC = "cyvk transport"


TRANSPORT_FEATURES = (xmpp.NS_DISCO_ITEMS,
                      xmpp.NS_DISCO_INFO,
                      xmpp.NS_RECEIPTS,
                      xmpp.NS_REGISTER,
                      xmpp.NS_GATEWAY,
                      xmpp.NS_VERSION,
                      xmpp.NS_CAPTCHA,
                      xmpp.NS_STATS,
                      xmpp.NS_VCARD,
                      xmpp.NS_DELAY,
                      xmpp.NS_PING,
                      xmpp.NS_LAST)
url = 'https://oauth.vk.com/authorize?client_id=%s&scope=%s&redirect_uri=' \
      'http://oauth.vk.com/blank.html&display=page&response_type=token'

APP_ID = 3789129
APP_SCOPE = 69634

URL_ACCEPT_APP = url % (APP_ID, APP_SCOPE)

LOG_LEVEL = logging.DEBUG
SLICE_STEP = 8
AVATAR_SIZE = "photo_100"
ALLOW_PUBLISH = False
DATABASE_FILE = "users.db"

REDIS_PREFIX = 'cyvk'
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

