from SQL import DB
from api_secrets import places_api_key, places_secret, places_client_id
import requests
from requests.auth import HTTPBasicAuth
import logging

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
        self.search_results: dict = {}

    def __str__(self):
        return "Google Places Searcher. Current city: " + self.city.name

    def search(self, term: str):
        # 'PRICE_LEVEL_INEXPENSIVE' == $1 - 10, 'PRICE_LEVEL_MODERATE' == $10 - 20

        response = requests.post(
            GooglePlaces.places_url,
            headers=GooglePlaces.headers,
            params={"key": places_api_key, "fields": GooglePlaces.fields},
            auth=HTTPBasicAuth(places_client_id, places_secret),
            data=str({"textQuery": term + " in  " + self.city.name})
        )

        if not check_code(response.status_code):
            return

        self.search_results = response.json()["places"]

        for entry in self.search_results:
            place = Place(
                entry.get("id"),
                entry.get("formattedAddress"),
                entry.get("rating"),
                entry.get("websiteUri"),
                entry.get("priceLevel"),
                entry.get("userRatingCount"),
                entry.get("displayName", {}).get("text"),
                entry.get("primaryTypeDisplayName", {}).get("text")
            )

            reviews = entry.get("reviews", {})

            self.add_reviews(place, reviews)

            try:
                place.category = place.category.lower()
            except AttributeError:
                # no category found, pass
                pass

            if not place.category:
                continue
            else:
                if "food" in place.category or "restaurant" in place.category:
                    self.city.restaurants.append(place)
                    DB.write("Places", vars(place))
                elif "market" in place.category or "grocery" in place.category:
                    self.city.grocery.append(place)
                    DB.write("Places", vars(place))
                elif "hospital" in place.category or "doctor" in place.category:
                    self.city.hospitals.append(place)
                    DB.write("Places", vars(place))
                else:
                    # support manual searching in a later version, for now place in other
                    DB.write("Places", vars(place))

    @staticmethod
    def add_reviews(place, reviews: dict):
        for review in reviews:

            review = Review(
                review.get("name"),
                review.get("relativePublishTimeDescription"),
                review.get("rating"),
                review.get("text", {}).get("text"),
                review.get("authorAttribution", {}).get("displayName"),
                review.get("authorAttribution", {}).get("photoUri"),
                review.get("googleMapsUri")
            )

            place.reviews.append(review)

class Place:

    table = "Places"

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