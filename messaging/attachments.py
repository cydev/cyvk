# coding: utf-8
from __future__ import unicode_literals
__all__ = ['parse_attachments']

import urllib
import compat

_logger = compat.get_logger()


def _wall(_):
    # Wall post
    return '\nWall: https://vk.com/feed?w=wall%(to_id)s_%(id)s'


def _photo(attachment):
    """
    Photo attachment representation generator.
    Just a link to photo
    """

    # trying to find largest possible image
    keys = ('src_xxxbig', 'src_xxbig', 'src_xbig', 'src_big', 'src', 'url', 'src_small')
    for k in keys:
        if k in attachment['photo']:
            return "\n" + attachment['photo'][k]


def _video(_):
    """
    Video attachment representation generator
    """
    return '\nVideo: http://vk.com/video%(owner_id)s_%(vid)s — %(title)s'


def _audio(attachment):
    """
    Audio attachment representation as search link
    """
    audio_search_url = 'https://vk.com/search?c[q]=%s&c[section]=audio'
    url = audio_search_url % urllib.quote(str('%(performer)s %(title)s' % attachment["audio"]))
    attachment['audio']['url'] = url
    return '\nAudio: %(performer)s — %(title)s — %(url)s'


def _doc(_):
    return '\nDocument: %(title)s — %(url)s'

_mapping = dict(wall=_wall, photo=_photo, video=_video, audio=_audio, doc=_doc)


def parse_attachments(_, msg):
    """
    Parse attachments to message
    """
    result = ''

    # No attachments, skipping
    if 'attachments' not in msg:
        return result

    _logger.debug('attachment found')

    attachments = msg["attachments"]

    # If there is a message with attachments, adding divider
    if msg['body']:
        result += 'Attachments:'

    for a in attachments:
        s = ''  # attachment representation
        key = a.get('type')
        try:
            # generating representation based on attachment type
            s += _mapping[key](a)
        except KeyError:
            # type not found
            _logger.error('Unknown attachment: %s' % a)
            s += "\nUnknown attachment: " + str(a[key])
        result += s % a.get(key, {})
    return result