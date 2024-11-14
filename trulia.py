import json
import requests
from bs4 import BeautifulSoup
import logging
from SQL import DB, check

headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US;en;q=0.9",
        "accept-encoding": "gzip, deflate"}

class Home:

    table = "Homes"

    def __init__(self, address, city, state, zip_code, link, desc, beds, bath, sqft, price, front_pic, available):
        self.address: str = address
        self.city: str = city
        self.state: str = state
        self.zip_code: str = zip_code
        self.link: str = link
        self.desc: str = desc
        self.beds: int = beds
        self.bath: int = bath
        self.sqft: int = sqft
        self.price: int = price
        # self.pictures: list[dict] = pictures # JSON data that contains picture links. Dict keys sorted by size
        self.front_pic: dict = front_pic
        self.available: bool = available
        self.score: int = 0

    def __str__(self):
        return self.address

class Picture:
    table = "Pictures"

    def __init__(self, home ,link, size):
        self.home: Home = home
        self.link: str = link
        self.size: str = size


class Trulia:

    table = "Trulia"

    # URL Format: https://www.trulia.com/{state abbreviation}/{city}

    def __init__(self, city, state):
        self.city: str = city
        self.state: str = state
        self.base_url = "https://www.trulia.com"
        self.data: dict = {}
        self.parsed_homes: int = 0
        self.current_link: str = "/".join(["https://www.trulia.com", self.state, self.city])
        self.current_page: int = 1
        self.on_last_page: bool = False

    def __str__(self):
        return f"Trulia Scraper. Current City: {self.city}, {self.state}"

    def go_to_next_page(self, soup):
        """Trulia will have the link to the next page under the following elements.
        If no elements are found, then we have reached the last page, and we return.
        Otherwise, we conduct another search"""

        self.current_page += 1

        nav = soup.find("nav", attrs={'aria-label': 'search results pagination'})
        nav = nav.find("li", attrs={'data-testid': "pagination-next-page"})

        if not nav:
            self.on_last_page = True
            return
        else:
            self.current_link = self.base_url + nav.find_all("a", href=True)[0]['href']
            self.on_last_page = False
            self.search()

    def search(self):

        tries: int = 0
        while tries <= 5:
            # There can occasionally be a connection issue in making the request.
            # This loop and try statement ensures that we continue trying even if we get the connection issue
            try:
                request = requests.get(self.current_link, headers=headers)
                break
            except requests.exceptions.ConnectionError as e:
                tries += 1
                logging.error(f"Unable to load page: {e}.\nTries Remaining: {5 - tries}")
                continue

        if tries > 5:
            logging.error("Trulia request failed. No data will be obtained on homes.")
            return

        soup = BeautifulSoup(request.content, 'html5lib')

        table = soup.find('script', attrs={'id': '__NEXT_DATA__'}).string

        table = table.replace("</script>", "")
        table = table.replace("<script id=\"__NEXT_DATA__\" type=\"application/json\" nonce="">", "")

        raw_data = json.loads(table)
        self.data = raw_data["props"]
        self.initialize_homes()

        while not self.on_last_page:
            logging.info(f"Going to next page. Current page: {self.current_page}")
            self.go_to_next_page(soup)


    def initialize_homes(self):
        logging.debug("Initializing homes...")
        for home in self.data['searchData']['homes']:

            self.parsed_homes += 1

            for size, link in home['media']['heroImage']['url'].items():
                picture = Picture(home, check(size), check(link))

            home = Home(check(home['location']['streetAddress']), check(home['location']['stateCode']),
                        check(home['location']['city']), check(home['location']['zipCode']),
                        check(home['url']), check(home['description']['value']),
                        check(home['bedrooms']['formattedValue']), check(home['bathrooms']['formattedValue']),
                        check(home['floorSpace']['formattedDimension']), check(home['price']['price']),
                        check(home['media']['heroImage']['url']['medium']), check(home['currentStatus']['isActiveForSale']))

            DB.write("Homes", vars(home))



def main():
    trulia = Trulia("NC", "Charlotte")

    x = trulia.search()


if __name__ == "__main__":
    main()