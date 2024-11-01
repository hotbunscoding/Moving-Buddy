import datetime
import praw
import requests
import requests.auth
from requests.auth import HTTPBasicAuth

from SQL import *
from secrets import *

logger = logging.getLogger(__name__)
logging.basicConfig(filename='debug.txt',
                    encoding='utf-8',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

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

class RedditBot:
    def __init__(self):
        self.name = "RedditBot"

class Reply(RedditBot):
    def __init__(self):
        super().__init__()
        self.dynamic_content: str = ""
        self.redditors_username = ""
        self.reply_in_progress: str = ""
        self.finalized_reply: str = ""
        self.team_stats = ""

    def construct_reply(self):
        self.finalized_reply = (
            f"Hey there {self.redditors_username}! "
            f"{self.dynamic_content}"
            f"Full Stats: {self.team_stats}"
            "{polls}"
        )

        return self.finalized_reply

    def add_dynamic_content(self, message_segment: str):
        self.dynamic_content += message_segment

    def add_team_stats(self, message_segment):
        self.team_stats += message_segment

    def reset(self):
        self.reply_in_progress: str = ""
        self.finalized_reply: str = ""

class SearchReddit(RedditBot):

    def __init__(self, city):
        super().__init__()
        self.session = None
        self.city = city
        self.city_subreddit = "" # testing, should be empty string in prod

    def authorize_reddit_session(self) -> object:
        user_agent = 'Python:moving_buddy.py:v0.1 (by /u/Pythonic_Bot)'

        # The following process requests the token
        client_auth = requests.auth.HTTPBasicAuth(reddit_client_id, reddit_secret)
        post_data = {"grant_type": "password",
                     "username": reddit_un,
                     "password": reddit_pw}

        headers = {"User-Agent": user_agent}
        response = requests.post("https://www.reddit.com/api/v1/access_token",
                                 auth=client_auth,
                                 data=post_data,
                                 headers=headers)

        if not response.status_code == 200:
            logging.warning(f"Request failed: {response.status_code}. "
                            f"Error requesting access token. Reddit API may be down or invalid credentials were passed")
            return

        access_token = response.json()['access_token']

        logging.info('Attempting to start Reddit session')

        self.session = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_secret,
            password=reddit_pw,
            user_agent=user_agent,
            username=reddit_un,
        )

        # The following process uses the token
        headers = {"Authorization": f"bearer {access_token}",
                   "User-Agent": user_agent}

        response = requests.get("https://oauth.reddit.com/api/v1/me",
                                headers=headers)

        response.json()
        print("Got here")
        return self.session

    def find_subreddit(self) -> tuple[str, bool]:

            if self.session is None:
                logging.error('PRAW session has not yet been initiated. Attempting to initiate now...')
                self.session = self.authorize_reddit_session()

            search_results: list[str] = []

            for subreddit in self.session.subreddits.search_by_name(self.city):
                if self.city == subreddit.display_name.lower():
                    self.city_subreddit = subreddit.display_name
                    exact_match = True
                    return self.city_subreddit, exact_match
                else:
                    search_results.append(subreddit.display_name)
                    continue

            exact_match = False
            print(search_results)
            self.city_subreddit = search_results[0]
            return self.city_subreddit, exact_match # no exact subreddits found, use first search result found

    def scrape_subreddit(self):
        subreddit = self.session.subreddit(self.city_subreddit)

        for submission in subreddit.stream.submissions():
            print(submission.title, submission.author)
            submission.comments.replace_more()
            reddit_post = RedditPost(submission, type="Submission")
            qualified = reddit_post.qualify_submission()
            reddit_post.add_to_relevant_comments() if qualified else None
            reddit_post.get_relevant_comments()

class RedditPost:

    def __init__(self, content, type=""):
        self.content = content  # submission instance
        self.text: str = ''
        self.city: str = 'Charlotte'
        self.type: str = type
        self.redditor: str = ''
        self.subreddit: str = ''
        self.score: int = 2
        self.qualified: bool = False

    def initialize(self) -> None:
        self.redditor = self.content.author.name
        self.subreddit = self.content.subreddit.display_name
        self.score = self.content.score
        self.text = self.content.body if self.type.lower() == "comment" else self.content.title
        self.content = str(self.content)

    def qualify_submission(self) -> bool:
        terms = ['move', 'moving', 'good place to', 'safe to', 'safety', 'unsafe', 'live here', 'living here', 'crime']

        # stats.track_parsed_submissions()
        self.initialize()
        self.score = 2
        DB.write('Comments', vars(self))
        for term in terms:
            if self.type == "Submission":
                if term in self.content.title.lower() or term in self.content.selftext.lower():
                    logging.info(f"{self.redditor}'s submission qualified. Term found: {term}")
                    self.qualified = True
                    # stats.track_match()
                    self.initialize()
                    return True
                else:
                    self.qualified = False

            else:
                if term in self.content.body.lower():
                    logging.info(f"{self.redditor}'s comment qualified. Term found: {term}")
                    self.qualified = True
                    # stats.track_match()
                    self.initialize()
                    return True
                else:
                    self.qualified = False

        return self.qualified

    def get_relevant_comments(self) -> object:
        logging.info(f"Grabbing comments for: {self.content.title} from {self.content.subreddit}")

        chat = ChatGPT(self.city)

        for comment in self.content.comments.list():
            print(comment.body)
            # stats.track_parsed_comments()
            reddit_comment = RedditPost(comment, type="Comment")
            qualified = reddit_comment.qualify_submission()
            DB.write('Comments', vars(reddit_comment))
            if not qualified:
                continue
            else:
                chat.relevant_comments.append(reddit_comment)
                continue

        return chat

    def add_to_relevant_comments(self):
        chat = ChatGPT(self.city)
        chat.relevant_comments = chat.relevant_comments.append(self.content)

class ChatGPT:

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {chat_gpt_key}",
    }
    role = "system"

    first_prompt = [
        {
            "role": role,
            "content": "You are an assistant helping me look for homes in a certain city. "
            "I gather relevant comments from the city's subreddit and then will send the comments to you. "
            "Please analyze these comments and, using your own words, give a summary of what the "
            "pros and cons are for living in this city",
        }
    ]

    def __init__(self, city):
        self.name = "ChatGPT"
        self.city = city
        self.history = ChatGPT.first_prompt
        self.relevant_comments = [] # comment instances
        self.comment_batch = []
        self.initialized = False

    def send_message(self, message):
        print(self.history, self.initialized)

        message_json = [{"role": ChatGPT.role, "content": message}]

        payload = {
            "model": "gpt-3.5-turbo-1106",
            "messages": message_json if self.initialized else ChatGPT.first_prompt,
            "max_tokens": 500,
            "temperature": 0.7,
        }

        self.initialized = True

        response = requests.post(ChatGPT.url, headers=ChatGPT.headers, json=payload)

        if not response.status_code == 200:
            logging.warning(
                f"Request failed: {response.status_code}. "
                f"ChatGPT API may be down at the moment or an error occurred in the request"
            )
            return
        else:
            chatbot_response = response.json()["choices"][0]["message"][
                "content"
            ].strip()

        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": chatbot_response})

        print(self.history, self.initialized)

        print(f"ChatGPT: {chatbot_response}")

    def flush_list(self):

        if not len(self.relevant_comments) >= 1000:
            logging.info(
                f"List flush criteria not met: {len(self.relevant_comments)} is less than 1000. "
                "Script will try again automatically at a later time."
            )
            return False
        else:
            logging.info("Saving... ")
            try:
                DB.write('Comments', self.relevant_comments)
            except Exception as e:
                logging.error(f'An error occurred: {e}. Returning...')
                return False

            logging.info("Saved to CSV. List flush successful. Returning...")
            self.relevant_comments.clear()

    def send_batch(self):
        logging.info(
            f"Total comments found: {len(self.comment_batch)}. Attempting to analyze..."
        )

        message = "Please analyze the next batch of comments: "

        if len(self.comment_batch) < 4:
            logging.info(
                f"Batch criteria not met: {len(self.comment_batch)} is less than 4). "
                f"Script will try again automatically at a later time."
            )
            return False
        else:
            for comment in self.comment_batch:
                message += comment
                message += "\n"

            self.send_message(message)

class Stats:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.up_time = 0
        self.parsed_submissions_count = 0
        self.parsed_comments_count = 0
        self.matched_comments_count = 0

    def get_up_time(self):
        self.up_time = (
            datetime.datetime.now() - self.start_time
        )
        return self.up_time

    def track_parsed_submissions(self):
        self.parsed_submissions_count += 1
        return self.parsed_submissions_count

    def track_parsed_comments(self):
        self.parsed_comments_count += 1
        return self.parsed_comments_count

    def track_match(self) -> int:
        self.matched_comments_count += 1
        return self.matched_comments_count

    def reset_stats(self):
        self.parsed_submissions_count = 0
        self.parsed_comments_count = 0

class Maps:
    # Google Maps
    maps_url = "https://maps.googleapis.com/maps/api/directions/"

    # maps = googlemaps.Client(key=key)
    def __init__(self):
        self.name = "Google Maps"
        self.destination = ""
        self.origin = ""

class Places:
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
        self.name = "Google Places"
        self.city = city  # city instance
        self.url = ""

    def restaurants(self):
        # 'PRICE_LEVEL_INEXPENSIVE' == $1 - 10, 'PRICE_LEVEL_MODERATE' == $10 - 20
        # Initialize request argument(s)
        response = requests.post(
            Places.places_url,
            headers=Places.headers,
            params={"key": places_api_key, "fields": Places.fields},
            auth=HTTPBasicAuth(places_client_id, places_secret),
            data='{"textQuery": "Hospitals in ' + self.city.name + '"}',
        )

        if not check_code(response.status_code):
            return False

        # Handle the response
        response = response.json()["places"]

        for restaurant_entry in response:
            try:
                restaurant = Restaurant(
                    restaurant_entry["id"],
                    restaurant_entry["formattedAddress"],
                    restaurant_entry["rating"],
                    restaurant_entry["websiteUri"],
                    restaurant_entry["priceLevel"],
                    restaurant_entry["userRatingCount"],
                    restaurant_entry["displayName"]["text"],
                    restaurant_entry["primaryTypeDisplayName"]["text"],
                )

                self.city.append(restaurant)

                print(restaurant.category)

            except KeyError as e:
                logging.error(f"Restaurant not saved - KeyError: {e}")
                continue

            reviews = restaurant_entry["reviews"]

            for review in reviews:

                try:
                    review = Review(
                        review["name"],
                        review["relativePublishTimeDescription"],
                        review["rating"],
                        review["text"]["text"],
                        review["authorAttribution"]["displayName"],
                        review["authorAttribution"]["photoUri"],
                        review["googleMapsUri"],
                    )

                    print(dir(review))
                except KeyError as e:
                    logging.error(f"Review not saved - KeyError: {e}")
                    continue

                restaurant.reviews.append(review)
                print(review.text)

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

class City:

    table = "Cities"

    def __init__(self, name):
        self.name: str = name
        self.restaurants: list = []  # list of restaurant instances
        self.hospitals: list = []  # list of hospital instances
        self.grocery: list = [] # list of grocery instances
        self.reddit: list = []  # list of RedditPost post/comment instances
        self.gpt: str = ""  # ChatGPT's analysis and summary of relevant Reddit comments

def main():
    """Main Program loop - START HERE"""
    city = City(str(input("What city would you like to explore? ")).lower())

    print(city.name)
    search = SearchReddit(city.name)
    subreddit, exact_match = search.find_subreddit()

    search.scrape_subreddit()

    if not exact_match:
        logging.info(f"No exact subreddits found for: {city}. Showing results for closest found: {subreddit}")

if __name__ == '__main__':
    main()