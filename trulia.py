import json
import requests
from bs4 import BeautifulSoup
import logging
from SQL import DB


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

    base_url = "https://www.trulia.com"
    # URL Format: https://www.trulia.com/{state abbreviation}/{city}

    def __init__(self, city, state):
        self.city: str = city
        self.state: str = state
        self.data: dict = {}

    def __str__(self):
        return f"Trulia Scraper. Current City: {self.city}, {self.state}"

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
        self.initialize_homes()

        return self.data

    def initialize_homes(self):
        logging.debug("Initializing homes...")
        for home in self.data['searchData']['homes']:
            try:
                for size, link in home['media']['heroImage']['url'].items():
                    picture = Picture(home, size, link)

                home = Home(home['location']['streetAddress'], home['location']['stateCode'], home['location']['city'],
                            home['location']['zipCode'], home['url'], home['description']['value'],
                            home['bedrooms']['formattedValue'],
                            home['bathrooms']['formattedValue'], home['floorSpace']['formattedDimension'],
                            home['price']['price'],  home['media']['heroImage']['url']['medium'], home['currentStatus']['isActiveForSale'])

                # print(home.zip_code + " " + home.city + " " + home.state + " " + home.address)
            except TypeError as e:
                logging.info(f"Item not found: {e}")
                continue

            print(home.front_pic)


            print(vars(home))
            print("Debugging: " + str(type(vars(home))))
            print(vars(picture))
            DB.write("Homes", vars(home))



def main():
    trulia = Trulia("NC", "Charlotte")

    x = trulia.search()


if __name__ == "__main__":
    main()