import xmltodict
import requests
import json
import datetime
from dateutil import parser

def getRSS(url: str) -> dict:
    response = requests.get(url)
    # print(response.content)
    return xmltodict.parse(response.content)

# with open("news.json", "r") as f:
#              ns = f.readlines()
# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)
# , "https://www.prnewswire.com/sitemap-news.xml?page=2", "https://www.prnewswire.com/sitemap-news.xml?page=3", "https://www.prnewswire.com/sitemap-news.xml?page=4", "https://www.prnewswire.com/sitemap-news.xml?page=5", "https://www.prnewswire.com/sitemap-news.xml?page=6", "https://www.prnewswire.com/sitemap-news.xml?page=7", "https://www.prnewswire.com/sitemap-news.xml?page=8", "https://www.prnewswire.com/sitemap-news.xml?page=9", "https://www.prnewswire.com/sitemap-news.xml?page=10"]
urls = ["https://www.prnewswire.com/sitemap-news.xml?page=1", "https://www.prnewswire.com/sitemap-news.xml?page=2", "https://www.prnewswire.com/sitemap-news.xml?page=3", "https://www.prnewswire.com/sitemap-news.xml?page=4", "https://www.prnewswire.com/sitemap-news.xml?page=5", "https://www.prnewswire.com/sitemap-news.xml?page=6", "https://www.prnewswire.com/sitemap-news.xml?page=7", "https://www.prnewswire.com/sitemap-news.xml?page=8", "https://www.prnewswire.com/sitemap-news.xml?page=9", "https://www.prnewswire.com/sitemap-news.xml?page=10"]

for url in urls:
    data = getRSS(url)
    print(data)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    # for item in data['urlset']['url']:
    #     if datetime.datetime.strptime((item["news:news"]["news:publication_date"])[:-6], "%Y-%m-%dT%H:%M:%S").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
    #          continue
    #     # print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
    #     # print(item['link'])
    #     fndata = {
    #          "title": item["news:news"]['news:title'],
    #         #  "description": item['description'],
    #          "date": item["news:news"]["news:publication_date"]
    #     }
    #     # print(fndata)
    #     # Convert `fndata` to a string for comparison
    #     fndata_str = json.dumps(fndata).strip()

    #     # Check if `fndata_str` exists in `ns`
    #     if not ns or not any(fndata_str == line.strip() for line in ns):
    #         with open("news.json", "a") as f:
    #             json.dump(fndata, f)
    #             f.write("\n")

    #         with open("newsforanalysis.txt", "a") as f:
    #             f.write(f"{item["news:news"]['news:title']}\n{item["news:news"]["news:publication_date"]}\n")
    #     else:
    #         print("Found, skipping write")
        # if not ns:
        #     with open("news.json", "a") as f:
        #             json.dump(fndata, f)
        #             f.write("\n")
        #     with open("newsforanalysis.txt", "a") as f:
        #             f.write(f"{item['title']}\n{item['description']}\n{item["pubDate"]}\n")
        # else:
        #     for line in ns:
        #         if json.dumps(fndata).strip() == line.strip():
        #                 print("found")
        #                 break
        #         else:
        #             print("not found")
        #             with open("news.json", "a") as f:
        #                 json.dump(fndata, f)
        #                 f.write("\n")
        #             with open("newsforanalysis.txt", "a") as f:
        #                     f.write(f"{item['title']}\n{item['description']}\n{item["pubDate"]}\n")
        #             print()
