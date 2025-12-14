import xmltodict
import requests
import json
import datetime

def getRSS(url: str) -> dict:
    response = requests.get(url)
    return xmltodict.parse(response.content)

# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)

with open("news.json", "r") as f:
             ns = f.readlines()

urls = ["https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['rss']['channel']['item']:
        if datetime.datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S +0000").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
             continue
        print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
        # print(item['link'])
        fndata = {
             "title": item['title'],
             "description": item['description'],
             "date": item["pubDate"]
        }
        # with open("news.json", "a") as f:
        #      json.dump(fndata, f)
        #      f.write("\n")
        # with open("currnews.txt", "a") as f:
        #         f.write(f"{item['title']}\n{item['description']}\n{item["pubDate"]}\n")
        # print()

                # Convert `fndata` to a string for comparison
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
