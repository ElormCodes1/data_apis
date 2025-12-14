import xmltodict
import requests
import json
import datetime

def getRSS(url: str) -> dict:
    response = requests.get(url)
    return xmltodict.parse(response.content)

with open("news.json", "r") as f:
             ns = f.readlines()

# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)
#  "https://feeds.skynews.com/feeds/rss/world.xml", "https://feeds.skynews.com/feeds/rss/uk.xml", 
urls = ["https://feeds.skynews.com/feeds/rss/business.xml","https://feeds.skynews.com/feeds/rss/technology.xml"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['rss']['channel']['item']:
        if datetime.datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S %z").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
             continue
        print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
        # print(item['link'])
        fndata = {
             "title": item['title'],
             "description": item['description'],
             "date": item["pubDate"]
        }

        fndata_str = json.dumps(fndata).strip()

        # Check if `fndata_str` exists in `ns`
        if not ns or not any(fndata_str == line.strip() for line in ns):
            with open("news.json", "a") as f:
                json.dump(fndata, f)
                f.write("\n")

            with open("newsforanalysis.txt", "a") as f:
                f.write(f"{item['title']}\n{item['description']}\n{item['pubDate']}\n")
        else:
            print("Found, skipping write")
        # with open("news.json", "a") as f:
        #      json.dump(fndata, f)
        #      f.write("\n")
        # with open("currnews.txt", "a") as f:
        #         f.write(f"{item['title']}\n{item['description']}\n{item["pubDate"]}\n")
        # print()
