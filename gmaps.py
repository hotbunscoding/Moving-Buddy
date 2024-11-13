import googlemaps
from secrets import places_api_key
from datetime import datetime
from unit_convert import UnitConvert

now = datetime.now()
maps = googlemaps.Client(key=places_api_key)

''' class Maps:
    # Google Maps
   #  maps_url = "https://maps.googleapis.com/maps/api/directions/"

    maps = googlemaps.Client(key=places_api_key)
    def __init__(self):
        self.name = "Google Maps"
        self.destination = ""
        self.origin = "" '''

class Score:
    """Score parent class will be used to calculate desirability among locations based on proximity.
    Overall score is contained in this group"""

    def __init__(self):
        self.restaurant_score: int = 0
        self.fun_score: int = 0
        self.grocery_score: int = 0
        self.overall_score: int = 0



class CalculateScore:

    def __init__(self, origin, destination):
        self.origin = origin
        self.destination = destination

    def walking_score(self) -> int:
        directions_result = maps.directions(origin=self.origin,
                                            destination=self.destination,
                                            departure_time=now,
                                            mode="walking")[0]

        score: int = 0

        distance: int = directions_result['legs'][0]['distance']['value']  # in meters
        duration: int = directions_result['legs'][0]['duration']['value']  # in seconds
        warnings: str = directions_result['warnings']

        print(duration)

        if not warnings:
            # If there are no warnings then it is likely a good route and walkable
            score += 3

        if duration <= 450:
            score += 7
        elif 450 < duration <= 900:
            score += 5
        elif 900 < duration <= 1800:
            score += 3
        elif duration >= 3600:
            score = 0  # anything above an hour is unwalkable so set to 0

        return score

    def driving_score(self) -> int:
        """Should add a disclaimer that this score is if the user were to leave right at this moment and may not
        reflect the necessarily best or worst conditions"""

        directions_result = maps.directions(origin=self.origin,
                                            destination=self.destination,
                                            departure_time=now,
                                            mode="driving")[0]

        distance: int = directions_result['legs'][0]['distance']['value']  # in meters
        duration: int = directions_result['legs'][0]['duration']['value']  # in seconds

        score: int = 0 # out of 10

        converted_distance = UnitConvert(meters=distance)['miles']
        converted_duration = UnitConvert(seconds=duration)['minutes']

        average: float = converted_distance / converted_duration

        # 6000 seconds is 1 hr 40 min - terrible for 60 miles
        # 4800 seconds is 1 hr 20 min - okay for 60 miles
        # 3600 seconds is 1 hr - great for 60 miles - 1.0 average
        # ideally should average a min/ a mile higher average is better

        if average >= 2:
            score += 10
        elif 2 > average >= 1:
            score += 8
        elif 1 > average >= 0.75:
            score += 6
        elif 0.75 > average >= 0.65:
            score += 4
        elif 0.65 > average >= 0.5:
            score += 3
        else:
            score += 1

        return score





# Place IDs must be prefixed with place_id:


def main():
    calculator = CalculateScore("Dunn, North Carolina 28334",
                                "Whole Foods Market, 8710 Six Forks Rd, Raleigh, NC 27615")
    print(calculator.driving_score())

if __name__ == '__main__':
    main()