# coding: utf
# This file is a part of VK4XMPP transport
# © simpleApps, 2013.

import urllib

GoogleMapLink = "https://maps.google.com/maps?q=%s"

def TimeAndDimensionInSpace(self, machine):
	body = str()
	if machine.has_key("geo"):
		WhereAreYou = machine["geo"]
		Place = WhereAreYou["place"]
		Coordinates = WhereAreYou["coordinates"].split()
		Coordinates = "Lat.: {0}°, long: {1}°".format(*Coordinates)
		body = _("Point on the map: \n")
		body += _("Country: %s") % Place["country"]
		body += _("\nCity: %s") % Place["city"]
		body += _("\nCoordinates: %s") % Coordinates
		body += "\n%s — Google Maps" % GoogleMapLink % urllib.quote(WhereAreYou["coordinates"])
	return body

Handlers["msg01"].append(TimeAndDimensionInSpace)