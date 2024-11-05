import json
import requests
from bs4 import BeautifulSoup
from bot_classes import RedditPost, City

headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "accept-language": "en-US;en;q=0.9",
        "accept-encoding": "gzip, deflate"}

class Trulia:

    table = "Trulia"

    base_url = "https://www.trulia.com"
    # URL Format: https://www.trulia.com/{state abbreviation}/{city}

    def __init__(self):
       pass

    def initialize(self):
        pass

    @staticmethod
    def search(state, city):
        base_url = "/".join([Trulia.base_url, state, city])
        request = requests.get(base_url, headers=headers)
        soup = BeautifulSoup(request.content, 'html5lib')

        table = soup.find('script', attrs={'id': '__NEXT_DATA__'}).string

        table = table.replace("</script>", "")
        table = table.replace("<script id=\"__NEXT_DATA__\" type=\"application/json\" nonce="">", "")

        raw_data = json.loads(table)

        return raw_data["props"]['searchData']['homes']

    def add_to_spreadsheet(self):
        data = {"Name": self.short_name, "Price": self.price, "Aisle": self.aisle, "Is Out of Stock?": self.is_out_of_stock,
                      "Rating": self.rating, "Review Count": self.review_count, "Category": self.category,
                      "Full Name": self.long_name, "Image Link": self.image, "Item Instance": self}

        csv_file = "item_reference.csv"



def main():
    charlotte = Trulia()

    x = charlotte.search("NC", "Charlotte")
    print(x)
    for i in x:
        print(i[['price']['price']])
        print(i[["url"]])

if __name__ == "__main__":
    main()