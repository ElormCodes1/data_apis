import xmltodict
import requests
import json
import datetime
from proxies import PROXY_LIST
from dotenv import load_dotenv
import  random

load_dotenv()

cookies = {
    'GUC': 'AQEBCAFn2ytoDkIgSQTW&s=AQAAAI44YzcA&g=Z9nkLA',
    'A1': 'd=AQABBMtqy2cCEASOiYeuneCH9EzCTIkE0owFEgEBCAEr22cOaEj2ySMA_eMBAAcIy2rLZ4kE0ow&S=AQAAAowHCWxvm3VDrb2TvY7SY88',
    'A3': 'd=AQABBMtqy2cCEASOiYeuneCH9EzCTIkE0owFEgEBCAEr22cOaEj2ySMA_eMBAAcIy2rLZ4kE0ow&S=AQAAAowHCWxvm3VDrb2TvY7SY88',
    'A1S': 'd=AQABBMtqy2cCEASOiYeuneCH9EzCTIkE0owFEgEBCAEr22cOaEj2ySMA_eMBAAcIy2rLZ4kE0ow&S=AQAAAowHCWxvm3VDrb2TvY7SY88',
    '_cb': 'DnwUvGCv5k-0DCwoG7',
    'PRF': 't%3DPRA%252BACN%252BUL%252BRI.PA%252BAPP%252BTNXP%252BESLT%252BAA%26theme%3Dauto',
    '_chartbeat2': '.1741384399522.1742588239205.100110000001111.BHB20SBMs47Ze75LyC8VGuTBNtp8g.1',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'if-modified-since': 'Fri, 21 Mar 2025 20:10:07 GMT',
    'if-none-match': '"cc6b304f9d2ef6a10cf42862270e9ff3"',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    # 'cookie': 'GUC=AQEBCAFn2ytoDkIgSQTW&s=AQAAAI44YzcA&g=Z9nkLA; A1=d=AQABBMtqy2cCEASOiYeuneCH9EzCTIkE0owFEgEBCAEr22cOaEj2ySMA_eMBAAcIy2rLZ4kE0ow&S=AQAAAowHCWxvm3VDrb2TvY7SY88; A3=d=AQABBMtqy2cCEASOiYeuneCH9EzCTIkE0owFEgEBCAEr22cOaEj2ySMA_eMBAAcIy2rLZ4kE0ow&S=AQAAAowHCWxvm3VDrb2TvY7SY88; A1S=d=AQABBMtqy2cCEASOiYeuneCH9EzCTIkE0owFEgEBCAEr22cOaEj2ySMA_eMBAAcIy2rLZ4kE0ow&S=AQAAAowHCWxvm3VDrb2TvY7SY88; _cb=DnwUvGCv5k-0DCwoG7; PRF=t%3DPRA%252BACN%252BUL%252BRI.PA%252BAPP%252BTNXP%252BESLT%252BAA%26theme%3Dauto; _chartbeat2=.1741384399522.1742588239205.100110000001111.BHB20SBMs47Ze75LyC8VGuTBNtp8g.1',
}

def getRSS(url: str) -> dict:
    response = requests.get(url, proxies={"http": random.choice(PROXY_LIST)}, headers=headers)
    return xmltodict.parse(response.content)

with open("news.json", "r") as f:
             ns = f.readlines()
# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)

urls = ["https://finance.yahoo.com/rss/"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['rss']['channel']['item']:
        if datetime.datetime.strptime(item["pubDate"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
             continue
        # print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
        # print(item['link'])
        fndata = {
             "title": item['title'],
            #  "description": item['description'],
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
                f.write(f"{item['title']}\n{item['pubDate']}\n")
        else:
            print("Found, skipping write")
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
