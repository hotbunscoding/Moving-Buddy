from bot_classes import *

def intro():
    print('''Welcome to Moving Buddy. This program is meant to assist in researching cities to move to.\n
    This program will use a variety of sources to determine city desirability including Reddit, 
    ChatGPT, Trulia, Google Places and Directions API.\n''')
    print('''Future roadmap is to support compartmentalization of features to allow users to only use one feature 
    at a time. Current functionality is to ask users for a city and then run all the features mentioned above.\n''')

def main():
    # city = input('Please enter a city name to research: ')
    # state = input('What state is this city in? Please enter the abbreviation:  ')

    city = City("Charlotte", "NC")

    trulia = Trulia(city.name, city.state)
    trulia.search()

if __name__ == '__main__':
    intro()
    main()