import googlemaps
from secrets import places_api_key

googlemaps.Client(key=places_api_key)

class Maps:
    # Google Maps
    maps_url = "https://maps.googleapis.com/maps/api/directions/"

    # maps = googlemaps.Client(key=key)
    def __init__(self):
        self.name = "Google Maps"
        self.destination = ""
        self.origin = ""