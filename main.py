from bot_classes import *

def clear_logs():
    open('debug.txt', 'w').close()

def main():
    moving_buddy = MainProgram()
    clear_logs()

    # 1. Search Trulia for Homes
    # moving_buddy.trulia.search()

    # print(f"Successfully collected data for {moving_buddy.trulia.parsed_homes} homes.")

    # moving_buddy.search_reddit()

    moving_buddy.search_places()

if __name__ == '__main__':
    main()