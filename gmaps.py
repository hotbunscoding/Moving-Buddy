from email.policy import default

import googlemaps
from secrets import places_api_key, places_secret, places_client_id
from datetime import datetime
from unit_convert import UnitConvert
import requests
from requests.auth import HTTPBasicAuth
import logging
from SQL import check

now = datetime.now()
maps = googlemaps.Client(key=places_api_key)

def check_code(status_code) -> bool:
    if status_code == 200:
        logging.info(f"Request successful: {status_code}")
        return True
    elif status_code == 401:
        logging.error(f"Request unauthorized: {status_code}")
        return False
    elif status_code == 403:
        logging.error(f"Request forbidden: {status_code}")
        return False
    elif status_code == 404:
        logging.error(f"Request Not Found: {status_code}")
        return False
    elif status_code == 500:
        logging.error(f"Request server error: {status_code}")
        return False
    else:
        return False

class GooglePlaces:
    # Google Places

    places_url = "https://places.googleapis.com/v1/places:searchText"  # &key=YOUR_API_KEY at the end of every URL

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {places_api_key}",
    }

    fields = (
        "places.id,places.displayName.text,places.primaryTypeDisplayName.text,places.formattedAddress,"
        "places.rating,places.websiteUri,places.priceLevel,places.userRatingCount,places.reviews"
    )

    def __init__(self, city):
        self.city = city  # city instance

    def __str__(self):
        return "Google Places Searcher. Current city: " + self.city.name

    def search(self, term):
        # 'PRICE_LEVEL_INEXPENSIVE' == $1 - 10, 'PRICE_LEVEL_MODERATE' == $10 - 20

        response = requests.post(
            GooglePlaces.places_url,
            headers=GooglePlaces.headers,
            params={"key": places_api_key, "fields": GooglePlaces.fields},
            auth=HTTPBasicAuth(places_client_id, places_secret),
            data=str({"textQuery": term + " in  " + self.city.name})
        )

        if not check_code(response.status_code):
            return False

        # Handle the response
        response = response.json()["places"]

        for restaurant_entry in response:


            restaurant = Restaurant(
                restaurant_entry.get("id"),
                restaurant_entry.get("formattedAddress"),
                restaurant_entry.get("rating"),
                restaurant_entry.get("websiteUri"),
                restaurant_entry.get("priceLevel"),
                restaurant_entry.get("userRatingCount"),
                restaurant_entry.get("displayName", {}).get("text"),
                restaurant_entry.get("primaryTypeDisplayName", {}).get("text")
            )

            self.city.restaurants.append(restaurant)

            print(restaurant.category)

            for i in vars(restaurant).values(): print(i)

            reviews = restaurant_entry["reviews"]

            for review in reviews:

                review = Review(
                    review.get("name"),
                    review.get("relativePublishTimeDescription"),
                    review.get("rating"),
                    review.get("text", "").get("text"),
                    review.get("authorAttribution", {}).get("displayName"),
                    review.get("authorAttribution", {}).get("photoUri"),
                    review.get("googleMapsUri")
                )

                restaurant.reviews.append(review)
                for i in vars(review).values(): print(i)

            print(restaurant_entry)

    def grocery(self):
        pass

    def hospitals(self):
        pass

    def search_all(self):
        pass


class Restaurant:

    table = "Restaurants"

    def __init__(
        self,
        places_id,
        address,
        rating,
        website,
        price_range,
        review_count,
        name,
        category,
    ):

        self.places_id: str = places_id
        self.address: str = address
        self.rating: float = rating
        self.website: str = website
        self.price_range: str = price_range
        self.review_count: int = review_count
        self.name: str = name
        self.category: str = category
        self.reviews: list = []  # list of review instances

class Hospital:

    table = "Hospitals"

    def __init__(
        self,
        places_id,
        address,
        rating,
        website,
        review_count,
        name,
        category,
    ):

        self.places_id: str = places_id
        self.address: str = address
        self.rating: float = rating
        self.website: str = website
        self.review_count: int = review_count
        self.name: str = name
        self.category: str = category
        self.reviews: list = []  # list of review instances

class Grocery:
    table = "Grocery"

    def __init__(self, places_id,
        address,
        rating,
        website,
        review_count,
        name,
        category,
        price_range
    ):

        self.places_id: str = places_id
        self.address: str = address
        self.rating: float = rating
        self.website: str = website
        self.review_count: int = review_count
        self.name: str = name
        self.category: str = category
        self.reviews: list = []  # list of review instances
        self.price_range: str = price_range

class Review:

    table = "Reviews"

    def __init__(self, places_id, posted, rating, text, author, photo, link):
        self.places_id: str = places_id
        self.posted: str = posted
        self.rating: float = rating
        self.text: str = text
        self.author: str = author
        self.photo: str = photo
        self.link: str = link

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

    def walking_score(self) -> int or None:
        directions_result = maps.directions(origin=self.origin,
                                            destination=self.destination,
                                            departure_time=now,
                                            mode="walking")[0]

        score: int = 0

        try:
            distance: int = directions_result['legs'][0]['distance']['value']  # in meters
            duration: int = directions_result['legs'][0]['duration']['value']  # in seconds
            warnings: str = directions_result['warnings']
        except KeyError as e:
            logging.error(f"Unable to calculate walking score: {e}")
            return

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

    def driving_score(self) -> int or None:
        """Should add a disclaimer that this score is if the user were to leave right at this moment and may not
        reflect the necessarily best or worst conditions"""

        directions_result = maps.directions(origin=self.origin,
                                            destination=self.destination,
                                            departure_time=now,
                                            mode="driving")[0]
        try:
            distance: int = directions_result['legs'][0]['distance']['value']  # in meters
            duration: int = directions_result['legs'][0]['duration']['value']  # in seconds
        except KeyError as e:
            logging.error(f"Unable to calculate driving score: {e}")
            return

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
    print(calculator.driving_score() if not None else "Error: Couldn't calculate driving score")

if __name__ == '__main__':
    main()