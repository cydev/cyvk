# coding: utf-8
# (с) simpleApps, 25.06.12; 19:58:42
# License: GPLv3.

import os
import config
import locale
import gettext
import logging

logger = logging.getLogger("vk4xmpp")

locale.setlocale(locale.LC_ALL, '') # use user's preferred locale
_ = gettext.gettext

# def setVars(lang, path):
#     globals()["locale"] = lang
#     globals()["path"] = path


# def rFile(name):
#     with open(name, "r") as file:
#         return file.read()


# def _(what):
#     locale_file_path = "%s/locales/locale.%s" % (config.LOCALE_PATH, config.LOCALE)
#     what = what.replace("\n", "\L")
#     if config.LOCALE != "en" and os.path.exists(locale_file_path):
#         data = open(locale_file_path).read()
#         for line in data.splitlines():
#             if line.startswith(what):
#                 what = line.split("=")[1]
#     return what.replace("\L", "\n")


def init_localization():
  """prepare l10n"""
  locale.setlocale(locale.LC_ALL, '') # use user's preferred locale
  # take first two characters of country code
  loc = locale.getlocale()
  filename = "locales/messages_%s.mo" % locale.getlocale()[0][0:2]

  try:
    logging.debug("Opening message file %s for locale %s", filename, loc[0])
    trans = gettext.GNUTranslations(open( filename, "rb"))
  except IOError:
    logging.debug("Locale not found. Using default messages")
    trans = gettext.NullTranslations()
  trans.install()
