# coding: utf

import library.xmpp as xmpp
from library.stext import _ as _
import logging

# Connection host.
# For Prosody "vk.example.com"
HOST = "s1.cydev"

# Connection server (usually equals host)
# For Prosody "example.com"
SERVER = "vk.s1.cydev"

# Connection port (as you set in your jabber-server config)
# Default value for Prosody is 5347
PORT = 5556

# Transport ID (Controls all)
TRANSPORT_ID = "vk.s1.cydev"

# Connection password.
PASSWORD = "secret"

# Default status (1 — online (recommended) / 0 — offline)
DEFAULT_STATUS = 1

# Use API feature lastMessageID (transport will save last user message id, 1 — use (recommended), 2 — not use)
USE_LAST_MESSAGE_ID = 1

## Language (ru/en/pl)
DefLang = "ru"

## Photo size (photo_50, photo_100, photo_200_orig)
PHOTO_SIZE = "photo_100"

## White list. Put here servers which you want allow to access transport. F.e.: ['yourserver1.tld','yourserver2.tld']
## Save it as [] if you won't block any servers.
WHITE_LIST = []

## Watcher list. Put here jid(s) of transport admin for notifications of registration. F.e.: ['admin@yourserver1.tld','name@yourserver2.tld']
## Save it as [] if you won't watch any registration.
WATCHER_LIST = []

# Additional about text. It was shown after main about text in transports vcard.
ADDITIONAL_ABOUT = ""

# Conference server. Don't change if you won't allow your users to use groupchats (depends from jabber-server's MUC)
# It's an alpha! Testers are welcome, but don't use it every time!
# F.e. conference.example.com
CONFERENCE_SERVER = ""

# Users limit. How much users can be stored on your server?
# Save as 0 if you won't limit registrations.
USER_LIMIT = 0

#! Danger zone.
#! Edit next settings ONLY IF YOU KNOW WHAT ARE YOU DOING! DEFAULT VALUES ARE RECOMMENTED!
## Thread stack size (WARNING: MAY CAUSE TRANSPORT CRASH WITH SEGMENTATION FAULT ERROR)
## It's needed for optimize memory consuming.
## minimum value is 32768 bytes (32kb)
THREAD_STACK_SIZE = 0

## Timeout when user considered inactive (seconds)
ACTIVE_TIMEOUT = 120

## Max roster update timeout (when user inactive, seconds)
ROSTER_TIMEOUT = 180

## Default roster update timeout (when user is active)
ROSTER_UPDATE_TIMEOUT = 6

## Maximum forwarded messages depth.
MAXIMUM_FORWARD_DEPTH = 5

## Image that will be used if transport can't recieve image from VK.
URL_VCARD_NO_IMAGE = "http://simpleapps.ru/vk4xmpp.png"

## Eval jid. jid for command "!eval"
EVAL_JID = ""

## Debug xmpppy library
DEBUG_XMPPPY = True

## Database file (as you like)
DB_FILE = "users.db"

## File used for storage PID.
PID_FILE = "pidFile.txt"

## Log file.
LOG_FILE = "vk4xmpp.log"

## Directory for storage crash logs.
CRASH_DIR = "crash"

IDENTIFIER = {"type": "vk",
                "category": "gateway",
                "name": "VK4XMPP Transport"}

BANNED_CHARS = [unichr(x) for x in xrange(32) if x not in (9, 10, 13)] + [unichr(57003)]

LOCALE = 'ru'

LOCALE_PATH = 'locales'

DESC = _("© simpleApps, 2013."
         "\nYou can support developing of any project"
         " via donation by WebMoney:"
         "\nZ405564701378 | R330257574689.")


transport_features = (xmpp.NS_DISCO_ITEMS,
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

URL_ACCEPT_APP = "http://simpleapps.ru/vk4xmpp.html"

LOG_LEVEL = logging.DEBUG
SLICE_STEP = 8
AVATAR_SIZE = "photo_100"
ALLOW_PUBLISH = False
DATABASE_FILE = "users.db"

