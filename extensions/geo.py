# coding: utf-8

import urllib

API_URL = "https://maps.google.com/maps?q=%s"

def parse_geo(_, machine):
    body = ""

    if "geo" not in machine:
        return body

    location = machine["geo"]
    place = location.get("place")
    coordinates = location["coordinates"].split()
    coordinates = "Lat.: {0}°, long: {1}°".format(*coordinates)
    body = _("Point on the map: \n")

    if place:
        body += "Country: %s" % place["country"]
        body += "\nCity: %s\n" % place["city"]

    body += "Coordinates: %s" % coordinates
    body += "\n%s — Google Maps" % API_URL % urllib.quote(location["coordinates"])

    return body