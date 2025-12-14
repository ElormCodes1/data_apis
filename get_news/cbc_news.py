import xmltodict
import requests
import json
import datetime
from bs4 import BeautifulSoup


cookies = {
    'referrerPillar': 'legacy',
    'referringDepartment': 'noreferrer',
    'bm_mi': '6063D41258217C1DBA9ABBE857E075C1~YAAQB/sTApnV7U6VAQAAh0tqURqBzpl1m0p8yjX2XGJX1+jY5BjyaiO5mpRJphGnk5Hww8RVRcFnm3HUdzK0ldsD+/iNW5/xwU6rlAl5PB5v0gKo4T1LbYKLcbGxXL42A8EFflh84v9H7ptYhe+01z+599dx4PxPBrNuOGCZJQ71BK8D6o11cYS7EAgtupzIeRMBWY+AySQgAEp7otTC4su5Nyj3MG1GTWwzJQnRnWM/9UPPCrrTYlC8hWJA/ezp0BZzQ2+4y5DA0FxcQV21X6dUVdwZGYKXxAtwYlPcQnAGUXvKlxOGlKAS9mvYcbef9ek=~1',
    'DATA_FEATURE_LINKS': '',
    'SC_LINKS': '',
    'ak_bmsc': '2BA53504B601525D1FFA1F2A974A1DF5~000000000000000000000000000000~YAAQB/sTAp0y7k6VAQAAb0OmURocr8zBiNLPC79C9iPPWTsuXdZJFZvptlM93OgBcCn1tlCXquJlyAfNszTp775u5B+2yJ5LeHenHKzCIqidDY4yTSjifSefwYaaOru2ZK2gcQ9K4Xp0erfEWR0yr7mesd8RYNF/txA0FjBROcnaquwWnsoVpvTLTry0inMqtTIkz4MmD44a0Sf0bDyIsve5lJW8cuHuD9gLr8bEThE4zTP+x/IWjK6YK+gV8OZKdrZFb9QmzO8AwDHVdpxsvNBzEnaPqHqaPrRl/NtTcYlT5Lf3U2v0NXdAnzSm6sppnWcMonakRb3UvFa+6RZgBP1VGqaGyy80eq/86CIU9nEIdEUk3LPi97VkfaGY36MvFnAyzShXvNsxLwhCDu+vgxfrzi5S+lCR4tfzCGOxszbl1dKaFk4DXV63',
    'bm_sv': '63D70E710E85617475EF16286479921F~YAAQB/sTAssy7k6VAQAAWF+mURqkKnQD/bbeNT9NkEDlHCvGgJY7XjDcCXT/siPyEbcTAYq4y1/5jFvuUSIFHYwj/6i2jMfvRoPK70d+mm+ifOsz6nW53HcumorBDhpHPsx3N67kMWgi2DFs4GeIRey9J///4tRQl9JjoHnVx9iPmUQd8yzIXPNqcTG8lkRms6DS20w5ARx/N+DBYoQ5bodziM2cqXqPrFSXIPRsDrbQpaDX8odz2gYoI/lrhshSLg==~1',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.8',
    'cache-control': 'max-age=0',
    # 'cookie': 'referrerPillar=legacy; referringDepartment=noreferrer; bm_mi=6063D41258217C1DBA9ABBE857E075C1~YAAQB/sTApnV7U6VAQAAh0tqURqBzpl1m0p8yjX2XGJX1+jY5BjyaiO5mpRJphGnk5Hww8RVRcFnm3HUdzK0ldsD+/iNW5/xwU6rlAl5PB5v0gKo4T1LbYKLcbGxXL42A8EFflh84v9H7ptYhe+01z+599dx4PxPBrNuOGCZJQ71BK8D6o11cYS7EAgtupzIeRMBWY+AySQgAEp7otTC4su5Nyj3MG1GTWwzJQnRnWM/9UPPCrrTYlC8hWJA/ezp0BZzQ2+4y5DA0FxcQV21X6dUVdwZGYKXxAtwYlPcQnAGUXvKlxOGlKAS9mvYcbef9ek=~1; DATA_FEATURE_LINKS=; SC_LINKS=; ak_bmsc=2BA53504B601525D1FFA1F2A974A1DF5~000000000000000000000000000000~YAAQB/sTAp0y7k6VAQAAb0OmURocr8zBiNLPC79C9iPPWTsuXdZJFZvptlM93OgBcCn1tlCXquJlyAfNszTp775u5B+2yJ5LeHenHKzCIqidDY4yTSjifSefwYaaOru2ZK2gcQ9K4Xp0erfEWR0yr7mesd8RYNF/txA0FjBROcnaquwWnsoVpvTLTry0inMqtTIkz4MmD44a0Sf0bDyIsve5lJW8cuHuD9gLr8bEThE4zTP+x/IWjK6YK+gV8OZKdrZFb9QmzO8AwDHVdpxsvNBzEnaPqHqaPrRl/NtTcYlT5Lf3U2v0NXdAnzSm6sppnWcMonakRb3UvFa+6RZgBP1VGqaGyy80eq/86CIU9nEIdEUk3LPi97VkfaGY36MvFnAyzShXvNsxLwhCDu+vgxfrzi5S+lCR4tfzCGOxszbl1dKaFk4DXV63; bm_sv=63D70E710E85617475EF16286479921F~YAAQB/sTAssy7k6VAQAAWF+mURqkKnQD/bbeNT9NkEDlHCvGgJY7XjDcCXT/siPyEbcTAYq4y1/5jFvuUSIFHYwj/6i2jMfvRoPK70d+mm+ifOsz6nW53HcumorBDhpHPsx3N67kMWgi2DFs4GeIRey9J///4tRQl9JjoHnVx9iPmUQd8yzIXPNqcTG8lkRms6DS20w5ARx/N+DBYoQ5bodziM2cqXqPrFSXIPRsDrbQpaDX8odz2gYoI/lrhshSLg==~1',
    'priority': 'u=0, i',
    'referer': 'https://www.cbc.ca/rss/',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
}

def getRSS(url: str) -> dict:
    response = requests.get(url, cookies=cookies, headers=headers)
    # print(response.text)
    return xmltodict.parse(response.content)

with open("news.json", "r") as f:
             ns = f.readlines()

# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)
# "https://www.cbc.ca/webfeed/rss/rss-topstories", "https://www.cbc.ca/webfeed/rss/rss-world", "https://www.cbc.ca/webfeed/rss/rss-canada", "https://www.cbc.ca/webfeed/rss/rss-politics",
urls = ["https://www.cbc.ca/webfeed/rss/rss-business", "https://www.cbc.ca/webfeed/rss/rss-technology"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['rss']['channel']['item']:
        try:
            if datetime.datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S EDT").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
                continue
        except:
            if datetime.datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S EST").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
                 continue

        title = item['title']
        description = item['description']
        des_soup = BeautifulSoup(description, "html.parser")
        description = des_soup.p.get_text() if des_soup.p else ""
        date = item['pubDate']
        print(f"{item['title']}\n{description}\n{item["pubDate"]}")

        fndata = {
             "title": item['title'],
             "description": item['description'],
             "date": item["pubDate"]
        }
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
        # print(item['link'])
        # fndata = {
        #      "title": item['title'],
        #      "description": item['description'],
        #      "date": item["pubDate"]
        # }
        # with open("news.json", "a") as f:
        #      json.dump(fndata, f)
        #      f.write("\n")
        # with open("currnews.txt", "a") as f:
        #         f.write(f"{item['title']}\n{description}\n{item["pubDate"]}\n")
        # print()