import datetime
import praw
import requests
import requests.auth
from SQL import *
from gmaps import GooglePlaces
from secrets import *
from trulia import Trulia, Home
from final_results import *


logger = logging.getLogger(__name__)
logging.basicConfig(filename='debug.txt',
                    encoding='utf-8',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')


def check(characteristic) -> str:
    if KeyError or TypeError:
        return "Not found"
    else:
        return characteristic

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
        self.history: list[dict] = []
        self.relevant_comments: list = [] # comment instances
        self.comment_batch: list = []
        self.initialized: bool = False

    def send_message(self, message):
        message_json = [{"role": ChatGPT.role, "content": message}]

        logging.debug(message_json)

        payload = {
            "model": "gpt-3.5-turbo-1106",
            "messages": message_json if self.initialized else ChatGPT.first_prompt,
            "max_tokens": 500,
            "temperature": 0.7,
        }

        logging.debug(f'Sending message to ChatGPT: {payload["messages"]}')
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

        logging.debug(f'Message received from ChatGPT: {chatbot_response}')
        print(f"ChatGPT: {chatbot_response}")

    def add_to_batch(self):
        logging.debug(self.relevant_comments)

        for comment in self.relevant_comments[:3]:
            self.comment_batch.append(comment.text)
            logging.debug(f"Batch added: {comment.text}\n")
        logging.debug(self.comment_batch)

        del self.relevant_comments[:3]

    def flush_list(self, forced=False):
        logging.info("Attempting list flush")
        if not len(self.relevant_comments) >= 1000 and not forced:
            logging.info(
                f"List flush criteria not met: {len(self.relevant_comments)} is less than 1000. "
                "Script will try again automatically at a later time."
            )
            return False
        else:
            logging.info("Saving... ")

            for comment in self.relevant_comments:
                try:
                    DB.write('Comments', vars(comment))
                    logging.debug("Comment saved successfully")
                except Exception as e:
                    logging.error(f'An error occurred: {e}. Comment not saved. Continuing...')
                    continue

            logging.info("Saved to CSV. List flush successful. Returning...")
            self.relevant_comments.clear()

    def send_batch(self):
        self.add_to_batch()

        message = "Please analyze the next batch of comments: "
        logging.debug(f"Current comment batch: {self.comment_batch}")
        if len(self.comment_batch) < 4:
            logging.info(
                f"Batch criteria not met: {len(self.comment_batch)} is less than 4. "
                f"Script will try again automatically at a later time."
            )
            return False
        else:
            for comment in self.comment_batch:
                message += ", " + comment if not self.comment_batch[0] else comment

            logging.info(
                f"Total comments found: {len(self.comment_batch)}. Attempting to analyze..."
            )

            logging.debug(message)

            self.send_message(message)

class SearchReddit:

    def __init__(self, city):
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

        logging.info('Attempting to initiate Reddit session...')

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
        logging.info("Reddit connection successful")
        return self.session

    def find_subreddit(self) -> tuple[str, bool]:
            """Looks for a given city's subreddit. If there is an exact match, returns True, else returns False.
            If there is not an exact match found, returns the closest matching subreddit"""

            if self.session is None:
                self.session = self.authorize_reddit_session()

            search_results: list[str] = []

            for subreddit in self.session.subreddits.search_by_name(self.city):
                if self.city.lower() == subreddit.display_name.lower():
                    self.city_subreddit = subreddit.display_name
                    exact_match = True
                    return self.city_subreddit, exact_match
                else:
                    search_results.append(subreddit.display_name)
                    continue

            exact_match = False
            logging.debug(f'Subreddits found: {search_results}')
            self.city_subreddit = search_results[0]
            return self.city_subreddit, exact_match # no exact subreddits found, use first search result found

    def scrape_subreddit(self):
        subreddit = self.session.subreddit(self.city_subreddit)

        gpt = ChatGPT("Charlotte")

        for submission in subreddit.stream.submissions():
            submission.comments.replace_more()
            reddit_post = RedditPost(submission, type="Submission")
            reddit_post.initialize()
            qualified = reddit_post.qualify_submission()
            reddit_post.add_to_relevant_comments() if qualified else None
            reddit_post.get_relevant_comments(gpt, auto_qualified=True if qualified else False)
            gpt.send_batch()
            gpt.flush_list()

class RedditPost:

    def __init__(self, content, type=""):
        self.content = content  # submission instance
        self.text: str = ''
        self.city: str = 'Charlotte'
        self.type: str = type
        self.redditor: str = ''
        self.subreddit: str = ''
        self.score: int = 0
        self.qualified: bool = False

    def __str__(self):
        return f"Redditor: {self.redditor}, Comment Snip: {self.text[:25]} Type: {self.type}"

    def initialize(self) -> None:
        self.redditor = self.content.author.name
        self.subreddit = self.content.subreddit.display_name
        self.score = self.content.score
        self.text = self.content.body if self.type.lower() == "comment" else self.content.title

    def qualify_submission(self) -> bool:
        terms = ['move', 'moving', 'good place to', 'safe to', 'safety', 'unsafe', 'live here', 'living here', 'crime']

        # stats.track_parsed_submissions()

        for term in terms:
            if self.type == "Submission":
                if term in self.content.title.lower() or term in self.content.selftext.lower():
                    # there has to be a better way to write these lol
                    logging.info(f"{self.content.author.name + "'s comment" if self.content.author.name is not None else 
                    "Error: Unable to find Redditor. Comment"} qualified. Term found: {term}")
                    try: logging.debug(self.content.title.lower())
                    except AttributeError: logging.debug(self.content.selftext.lower())
                    self.qualified = True
                    # stats.track_match()
                    self.initialize()
                    return True
                else:
                    self.qualified = False

            else:
                if term in self.content.body.lower():
                    # there has to be a better way to write these lol
                    logging.info(f"{self.content.author.name + "'s comment" if self.content.author.name is not None else 
                    "Error: Unable to find Redditor. Comment"} qualified. Term found: {term}")
                    logging.debug(self.content.body.lower())
                    self.qualified = True
                    # stats.track_match()
                    self.initialize()
                    return True
                else:
                    self.qualified = False

        return self.qualified

    def get_relevant_comments(self, gpt, auto_qualified=False):
        """auto_qualified parameter is used to automatically qualify all comments under a qualified submission since
        those comments will likely pertain to moving even though there won't be matched terms"""

        logging.info(f"Grabbing comments for post. Info:\n{self}")

        if auto_qualified:
            logging.info(f"{auto_qualified=} . All comments underneath this submission automatically qualify")

        for comment in self.content.comments.list():
            # stats.track_parsed_comments()
            reddit_comment = RedditPost(comment, type="Comment")
            qualified = reddit_comment.qualify_submission()
            if not qualified and not auto_qualified:
                continue
            else:
                reddit_comment.initialize()
                DB.write('Comments', vars(reddit_comment))
                gpt.relevant_comments.append(reddit_comment)
                continue

    def add_to_relevant_comments(self):
        chat = ChatGPT(self.city)
        chat.relevant_comments = chat.relevant_comments.append(self.content)

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


class City:

    table = "Cities"
    results = FinalResults()

    def __init__(self, name, state):
        self.name: str = name
        self.state: str = state # abbreviation
        self.restaurants: list = []  # restaurant instances
        self.hospitals: list = []  # hospital instances
        self.grocery: list = [] # grocery instances
        self.reddit: list = []  # RedditPost post/comment instances
        self.homes: list = [] # home instances
        self.gpt: str = ""  # ChatGPT's analysis and summary of relevant Reddit comments
        self.score: int = 0


    def __str__(self):
        return self.name + ", " + self.state


class MainProgram:

    def __init__(self):
        self.city: City = self.start()
        self.trulia = Trulia(self.city.name, self.city.state)
        self.reddit = SearchReddit(self.city.name)
        self.places = GooglePlaces(self.city)

    def __str__(self):
        return "Menu"

    def start(self):
        """Main Program loop - START HERE"""

        print('''Welcome to Moving Buddy. This program is meant to assist in researching cities to move to.\n
    This program will use a variety of sources to determine city desirability including Reddit, 
    ChatGPT, Trulia, Google Places and Directions API.\n''')
        print('''Future roadmap is to support compartmentalization of features to allow users to only use one feature 
    at a time. Current functionality is to ask users for a city and then run all the features mentioned above.\n''')

        # city = input('Please enter a city name to research: ')
        # state = input('What state is this city in? Please enter the abbreviation:  ')

        self.city = City("Charlotte", "NC")

        return self.city # lol

    def search_reddit(self):
        subreddit, exact_match = self.reddit.find_subreddit()

        if not exact_match:
            logging.info(f"No exact subreddits found for: {self.city.name}. "
                         f"Showing results for closest found: {subreddit}")

        self.reddit.scrape_subreddit()

    def search_places(self):
        terms = ['ethnic food', 'asian restaurants', 'grocery stores', 'hospitals']

        for term in terms:
            print(term)
            self.places.search(term)




def main():
    open('debug.txt', 'w').close()
    city = City("Charlotte", "NC")
    trulia = Trulia(city.name, "NC")
    trulia.search()

if __name__ == '__main__':
    main()