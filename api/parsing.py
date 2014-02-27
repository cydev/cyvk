# coding=utf-8
from __future__ import unicode_literals
from datetime import datetime
import re
import urllib

from .api import ApiWrapper
import compat
from config import BANNED_CHARS, MAXIMUM_FORWARD_DEPTH


_logger = compat.get_logger()
escape_name = re.compile("[^-0-9a-zа-яёë\._\' ґїє]", re.IGNORECASE | re.UNICODE | re.DOTALL).sub
escape = re.compile("|".join(BANNED_CHARS)).sub
sorting = lambda b_r, b_a: b_r["date"] - b_a["date"]
API_GOOGLE_MAPS = 'https://maps.google.com/maps?q=%s'


class MessageParser(ApiWrapper):
    def _parse_forwarded_messages(self, msg, depth=0):
        if 'fwd_messages' not in msg:
            return ''

        body = '\nForward messages:'

        for fwd in sorted(msg['fwd_messages'], sorting):
            id_from = fwd['uid']
            date = fwd['date']
            fwd_body = escape('', compat.html_unespace(fwd['body']))
            date = datetime.fromtimestamp(date).strftime('%d.%m.%Y %H:%M:%S')
            name = self.api.user.get(id_from)['name']
            body += "\n[%s] <%s> %s" % (date, name, fwd_body)
            body += self._parse_attachments(fwd)

            if depth < MAXIMUM_FORWARD_DEPTH:
                body += self._parse_forwarded_messages(fwd, depth + 1)

        return body

    @staticmethod
    def _parse_geo(msg):
        if 'geo' not in msg:
            return ''

        location = msg['geo']
        place = location.get('place')
        coordinates = location['coordinates'].split()
        coordinates = 'Lat.: {0}°, long: {1}°'.format(*coordinates)
        body = 'Point on the map: \n'

        if place:
            body += 'Country: %s\n' % place['country']
            body += 'City: %s\n' % place['city']

        body += 'Coordinates: %s\n' % coordinates
        body += '%s — Google Maps' % API_GOOGLE_MAPS % urllib.quote(location['coordinates'])

        return body

    def parse(self, message):
        body = ''
        for k in self._mapping:
            if k in message:
                body += self._mapping[k](message)
        return body

    @staticmethod
    def _parse_wall():
        # Wall post
        return '\nWall: https://vk.com/feed?w=wall%(to_id)s_%(id)s'

    @staticmethod
    def _parse_photo(attachment):
        """Photo attachment representation generator"""
        # trying to find largest possible image
        keys = ('src_xxxbig', 'src_xxbig', 'src_xbig', 'src_big', 'src', 'url', 'src_small')
        for k in keys:
            if k in attachment['photo']:
                return "\n" + attachment['photo'][k]

    @staticmethod
    def _parse_video(_):
        """Video attachment representation generator"""
        return '\nVideo: http://vk.com/video%(owner_id)s_%(vid)s — %(title)s'

    @staticmethod
    def _parse_audio(attachment):
        """Audio attachment representation as search link"""
        audio_search_url = 'https://vk.com/search?c[q]=%s&c[section]=audio'
        url = audio_search_url % urllib.quote(str('%(performer)s %(title)s' % attachment["audio"]))
        attachment['audio']['url'] = url
        return '\nAudio: %(performer)s — %(title)s — %(url)s'

    @staticmethod
    def _parse_document(_):
        return '\nDocument: %(title)s — %(url)s'

    def _parse_attachments(self, msg):
        """Parse attachments to message"""
        result = ''
        if 'attachments' not in msg:  # No attachments, skipping
            return result

        _logger.debug('attachment found')
        attachments = msg["attachments"]

        if msg['body']:  # If there is a message with attachments, adding divider
            result += 'Attachments:'

        for a in attachments:
            s = ''  # attachment representation
            key = a.get('type')
            try:
                s += self._attachments_mapping[key](a)  # generating representation based on attachment type
            except KeyError:
                _logger.error('Unknown attachment: %s' % a)
                s += "\nUnknown attachment: " + str(a[key])
            result += s % a.get(key, {})
        return result

    _attachments_mapping = dict(wall=_parse_wall, photo=_parse_photo, video=_parse_video, audio=_parse_audio,
                                doc=_parse_document)
    _mapping = {'geo': _parse_geo, 'fwd_messages': _parse_forwarded_messages, 'attachments': _parse_attachments}