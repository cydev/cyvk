# coding=utf-8
from __future__ import unicode_literals

import re
from config import BANNED_CHARS

escape_name = re.compile("[^-0-9a-zа-яёë\._\' ґїє]", re.IGNORECASE | re.UNICODE | re.DOTALL).sub
escape = re.compile("|".join(BANNED_CHARS)).sub
sorting = lambda b_r, b_a: b_r["date"] - b_a["date"]