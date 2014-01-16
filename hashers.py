from __future__ import unicode_literals

from hashlib import sha1
import string

def base_encode(number, base=0):
    if isinstance(number, str):
        if number == '':
            number = 0
        number = long(number)
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
    if number < 0:
        raise ValueError('number must be positive')
    if base < 0:
        raise ValueError('base must be > 0 (%s !> 0)' % base)

    alphabet = string.digits + string.ascii_letters

    if base > len(alphabet):
        raise ValueError('base is too big (%s>%s)' % (base, len(alphabet)))

    if base == 0:
        base = len(alphabet)

    base_n = ''
    while number:
        number, i = divmod(number, base)
        base_n = alphabet[i] + base_n

    return base_n or alphabet[0]


def get_hash(msg):
    try:
        int_hash = int(sha1(msg).hexdigest(), 16)
        return base_encode(int_hash)
    except TypeError:
        return None
    except UnicodeEncodeError:
        int_hash = int(sha1(msg.encode('utf-8')).hexdigest(), 16)
        return base_encode(int_hash)