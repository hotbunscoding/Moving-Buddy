import sqlite3 as sql
import logging

from bot_classes import RedditPost, Restaurant, Review, City

logger = logging.getLogger(__name__)
logging.basicConfig(filename='debug.txt',
                    encoding='utf-8',
                    level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

class DB: #Database

    initialized = False

    def __init__(self):
        self.name = "SQLite 3"

    @classmethod
    def initialize(cls):
        if not DB.initialized:
            logging.info("Initializing database and creating tables. Please wait...")
            conn = sql.connect('test.db')
            cursor = conn.cursor()

            restaurants = ("CREATE TABLE IF NOT EXISTS Restaurants( "
          "Name VARCHAR(100),"
          "places_id VARCHAR(200),"
          "address VARCHAR(200),"
          "rating FLOAT,"
          "website VARCHAR(200),"
          "price_range VARCHAR(30),"
          "review_count INTEGER,"
          "category VARCHAR(75),"
          "reviews VARCHAR(75))")


            reviews = ("CREATE TABLE IF NOT EXISTS Reviews(places_id "
                       "VARCHAR(200), "
                       "posted VARCHAR(50), "
                       "rating FLOAT, "
                       "text VARCHAR(750), "
                       "author VARCHAR(35), "
                       "photo VARCHAR(75), "
                       "link VARCHAR(75))")

            cities = ("CREATE TABLE IF NOT EXISTS Cities ("
                      "Name VARCHAR(50), "
                      "restaurants CHAR(50), "
                      "hospitals CHAR(50), "
                      "grocery CHAR(50), "
                      "reddit CHAR(50), "
                      "gpt CHAR(50))")

            comments = ("CREATE TABLE IF NOT EXISTS Comments ("
                      "Object VARCHAR(25), "
                        "Text VARCHAR(500), "
                      "City VARCHAR(50), "
                      "Type VARCHAR(12), "
                      "Redditor VARCHAR(50), "
                      "Subreddit VARCHAR(50), "
                      "Score INTEGER,"
                      " Qualified BOOLEAN)")

            cursor.execute(restaurants)
            cursor.execute(reviews)
            cursor.execute(cities)
            cursor.execute(comments)

            cursor.close()

            logging.info("Database has been initialized and tables have been created. Returning...")
            DB.initialized = True
        else:
            logging.info("Database already initialized. Returning...")
        return DB.initialized

    @staticmethod
    def write(table, values: list or dict):
        if not DB.initialized:
            DB.initialize()

        conn = sql.connect('test.db') # replace with 'home_helper.db' in prod
        cursor = conn.cursor()

        reviews_query = "INSERT INTO Reviews VALUES("
        restaurants_query = "INSERT INTO Restaurants VALUES("
        cities_query = "INSERT INTO Cities VALUES("
        comments_query = "INSERT INTO Comments VALUES("

        if table.lower() == "restaurants":
            query = restaurants_query
        elif table.lower() == "cities":
            query = cities_query
        elif table.lower() == "comments":
            query = comments_query
        elif table.lower() == "reviews":
            query = reviews_query
        else:
            logging.error("Table not found. Returning...")
            return

        def check_custom_isinstance(object) -> bool:
            if isinstance(object, RedditPost) or isinstance(object, Restaurant) or isinstance(object, Review) or isinstance(object, City):
                return True
            else:
                return False

        if isinstance(values, dict):
            last_item = list(values.values())[-1]
            print(last_item)
            data = []
            for value in values.values():
                if check_custom_isinstance(value):
                    data.append(str(value))
                logging.debug(f'Attempting to add {value} to SQL query')
                query += "?, " if last_item != value else "?)"
                data.append(value)

            print(data)
            print(query)
            cursor.execute(query, data)

        else:
            last_item = values[-1]

            for value in values.values():
                logging.debug(f'Attempting to add {value} to SQL query')
                query += "?, " if last_item != value else "?)"

            cursor.execute(query, values)

        conn.commit()
        cursor.close()

def main():
    sql = DB()
    sql.initialize()


if __name__ == '__main__':
    main()