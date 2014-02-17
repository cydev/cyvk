from config import REDIS_PREFIX

EVENTS_KEY = ':'.join([REDIS_PREFIX, 'events'])
NAME_KEY = 'name'
# user removed from transport
USER_REMOVED = 'user_removed'
# user registered via form
USER_REGISTERED = 'user_registered'
# user added
USER_ONLINE = 'user_online'
# long-polling start request
LP_REQUEST = 'lp_request'

all_events = {USER_REGISTERED, USER_REMOVED, USER_ONLINE}