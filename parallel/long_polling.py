from __future__ import unicode_literals

import json


from api.vkapi import method
from parallel import realtime, updates
from config import POLLING_WAIT
from compatibility import urlopen

import logging

logger = logging.getLogger("cyvk")

__author__ = 'ernado'


import sys

class TailRecurseException:
  def __init__(self, args, kwargs):
    self.args = args
    self.kwargs = kwargs

def tail_call_optimized(g):
  """
  This function decorates a function with tail call
  optimization. It does this by throwing an exception
  if it is it's own grandparent, and catching such
  exceptions to fake the tail call optimization.

  This function fails if the decorated
  function recurses in a non-tail context.
  """
  def func(*args, **kwargs):
    f = sys._getframe()
    if f.f_back and f.f_back.f_back \
        and f.f_back.f_back.f_code == f.f_code:
      raise TailRecurseException(args, kwargs)
    else:
      while 1:
        try:
          return g(*args, **kwargs)
        except TailRecurseException as e:
          args = e.args
          kwargs = e.kwargs
  func.__doc__ = g.__doc__
  return func


@tail_call_optimized
def _long_polling_get(jid):
    if realtime.is_polling(jid):
        logger.debug('already polling %s' % jid)
        return

    realtime.set_polling(jid)
    logger.debug('getting data via long polling')
    long_polling = method('messages.getLongPollServer', jid)
    long_polling['wait'] = POLLING_WAIT
    url = 'http://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode=2'.format(**long_polling)
    logger.debug('got url, starting polling')
    realtime.wait_for_api_call(jid)
    data = json.loads(urlopen(url).read())
    logger.debug('got data from polling server')
    realtime.unset_polling(jid)

    if not data['updates']:
        logger.debug('no updates for %s' % jid)
        return _long_polling_get(jid)

    for update in data['updates']:
        updates.process_data(jid, update)

    if realtime.is_client(jid):
        _long_polling_get(jid)
    else:
        logger.debug('finishing polling for %s' % jid)
    # process_client(jid)