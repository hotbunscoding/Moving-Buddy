import json
import requests
from bs4 import BeautifulSoup

headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US;en;q=0.9",
        "accept-encoding": "gzip, deflate"}

class Home:
    table = "Homes"

    def __init__(self, address, link, desc, beds, bath, sqft, price, pictures, available):
        self.address: str = address
        self.link: str = link
        self.desc: str = desc
        self.beds: int = beds
        self.bath: int = bath
        self.sqft: int = sqft
        self.price: int = price
        self.pictures: list[dict] = pictures  # JSON data that contains picture links. Dict keys sorted by size
        self.available: bool = available

class Trulia:

    table = "Trulia"

    base_url = "https://www.trulia.com"
    # URL Format: https://www.trulia.com/{state abbreviation}/{city}

    def __init__(self, city, state):
        self.city: str = city
        self.state: str = state
        self.data: list[dict] = []

    def __str__(self):
        return f"Trulia Scraper. Current city: {self.city}, {self.state}"

    def search(self):
        base_url = "/".join([Trulia.base_url, self.state, self.city])
        request = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(request.content, 'html5lib')

        table = soup.find('script', attrs={'id': '__NEXT_DATA__'}).string

        table = table.replace("</script>", "")
        table = table.replace("<script id=\"__NEXT_DATA__\" type=\"application/json\" nonce="">", "")

        raw_data = json.loads(table)

        # ['searchData']['homes']
        self.data = raw_data["props"]

        return self.data

    def initialize_homes(self):
        for home in self.data['searchData']['homes']:
            home = Home(home['location']['streetAddress'], home['url'])


def main():
    charlotte = Trulia("NC", "Charlotte")

    x = charlotte.search()


if __name__ == "__main__":
    main()