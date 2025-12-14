import xmltodict
import requests
import json
import datetime
from proxies import PROXY_LIST
from dotenv import load_dotenv
import random

load_dotenv()


cookies = {
    '__cf_bm': 'llgOTR1U8ElcL.IhyTIhNuZKas07bBl.E.UA_OWv.wc-1743582285-1.0.1.1-ycm79gaRKWZuhE9GOa2wEDmyYsR13rtxu0VpiQTqEPooBmx19YF5tUqM.bUCZ60F2qZ_KHTma77sD81Bet.vd6g3eha8tewDCp9.f0rWwhtE0NGr_EeNqLSq7RxBrSTj',
    'gcc': 'GH',
    'gsc': 'AA',
    'udid': 'de78f2278527b0dda1952aac119f1d01',
    'smd': 'de78f2278527b0dda1952aac119f1d01-1743582285',
    'invab': 'adconf_1|adesm_1|keysignup_0|mwebd_1|noadnews_1|ovpromo_2|regwall_1',
    '__cflb': '02DiuGRugds2TUWHMkkPGro65dgYiP188CoViPPTEPv3W',
    '_imntz_error': '0',
    'adBlockerNewUserDomains': '1743582286',
    'ses_num': '1',
    'last_smd': 'de78f2278527b0dda1952aac119f1d01-1743582285',
    'cf_clearance': 'u2CKBWqTKYgfjoauTABvRP5LvbL5F9d1cGIupFTg0CM-1743582287-1.2.1.1-fZVNpXAGajUGvvZ31G7ii2JBStsxXVTUtFYLnp9JWQmNDQxuyXl864OSFnuhRUlyn7UUHmJ_Ib6tiN1ugCHK1iaUPX9iB7q_kp_GblLSoGkQa9IP1AzKJ1sWyL4CeRoANKwL8VkfPfmOI4NnL0X2JFM8nnKKQlvvigu0H9Y3WbNshsKp8sDcF9PNiQhNVBV8Anjs4unJptojSq8AWo27d79xloJXB9vYsxjbqv2YJj3yrqtGtZbsmKr5meyuBY73Bf2HkBfjj2dxsdGUEv3aDRAoa3sIbAQslPJrGA8sRaRe7R_ohz9m9fLwpA2DqaGpcq7gQzM2o_5gVtzOmV6XOpZNDbiuSa0G4idQOhfvBPM',
    '__eventn_id': 'de78f2278527b0dda1952aac119f1d01',
    'r_p_s_n': '1',
    'reg_trk_ep': 'google%20one%20tap',
    'invpc': '3',
    'page_view_count': '3',
    'lifetime_page_view_count': '3',
    '_dd_s': 'aid=091650c9-b909-43be-9455-9f9eacff3804&logs=1&id=5b782707-3e9d-4ee0-a107-28a533f3e3a4&created=1743582286396&expire=1743583268241',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'if-modified-since': 'Wed, 02 Apr 2025 08:25:48 GMT',
    'if-none-match': '"648e5-631c7668a8d0c-gzip"',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    # 'cookie': '__cf_bm=llgOTR1U8ElcL.IhyTIhNuZKas07bBl.E.UA_OWv.wc-1743582285-1.0.1.1-ycm79gaRKWZuhE9GOa2wEDmyYsR13rtxu0VpiQTqEPooBmx19YF5tUqM.bUCZ60F2qZ_KHTma77sD81Bet.vd6g3eha8tewDCp9.f0rWwhtE0NGr_EeNqLSq7RxBrSTj; gcc=GH; gsc=AA; udid=de78f2278527b0dda1952aac119f1d01; smd=de78f2278527b0dda1952aac119f1d01-1743582285; invab=adconf_1|adesm_1|keysignup_0|mwebd_1|noadnews_1|ovpromo_2|regwall_1; __cflb=02DiuGRugds2TUWHMkkPGro65dgYiP188CoViPPTEPv3W; _imntz_error=0; adBlockerNewUserDomains=1743582286; ses_num=1; last_smd=de78f2278527b0dda1952aac119f1d01-1743582285; cf_clearance=u2CKBWqTKYgfjoauTABvRP5LvbL5F9d1cGIupFTg0CM-1743582287-1.2.1.1-fZVNpXAGajUGvvZ31G7ii2JBStsxXVTUtFYLnp9JWQmNDQxuyXl864OSFnuhRUlyn7UUHmJ_Ib6tiN1ugCHK1iaUPX9iB7q_kp_GblLSoGkQa9IP1AzKJ1sWyL4CeRoANKwL8VkfPfmOI4NnL0X2JFM8nnKKQlvvigu0H9Y3WbNshsKp8sDcF9PNiQhNVBV8Anjs4unJptojSq8AWo27d79xloJXB9vYsxjbqv2YJj3yrqtGtZbsmKr5meyuBY73Bf2HkBfjj2dxsdGUEv3aDRAoa3sIbAQslPJrGA8sRaRe7R_ohz9m9fLwpA2DqaGpcq7gQzM2o_5gVtzOmV6XOpZNDbiuSa0G4idQOhfvBPM; __eventn_id=de78f2278527b0dda1952aac119f1d01; r_p_s_n=1; reg_trk_ep=google%20one%20tap; invpc=3; page_view_count=3; lifetime_page_view_count=3; _dd_s=aid=091650c9-b909-43be-9455-9f9eacff3804&logs=1&id=5b782707-3e9d-4ee0-a107-28a533f3e3a4&created=1743582286396&expire=1743583268241',
}

def getRSS(url: str) -> dict:
    response = requests.get(url, headers=headers, proxies={"http": random.choice(PROXY_LIST)}, cookies=cookies)
    print(response.text)
    return xmltodict.parse(response.content)

with open("news.json", "r") as f:
             ns = f.readlines()
# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)

urls = ["https://www.investing.com/news_sitemap.xml", "https://www.investing.com/news_company_sitemap.xml", "https://www.investing.com/news_insider_trading_sitemap.xml", "https://www.investing.com/news_stock_market_sitemap.xml"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['urlset']['url']:
        if datetime.datetime.strptime(item["news:news"]["news:publication_date"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
             continue
        # print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
        # print(item['link'])
        fndata = {
             "title": item["news:news"]['news:title'],
            #  "description": item['description'],
             "date": item["news:news"]["news:publication_date"]
        }
        # Convert `fndata` to a string for comparison
        fndata_str = json.dumps(fndata).strip()
        print(fndata_str)

        # Check if `fndata_str` exists in `ns`
        # if not ns or not any(fndata_str == line.strip() for line in ns):
        #     with open("news.json", "a") as f:
        #         json.dump(fndata, f)
        #         f.write("\n")

        #     with open("newsforanalysis.txt", "a") as f:
        #         f.write(f"{item["news:news"]['news:title']}\n{item["news:news"]["news:publication_date"]}\n")
        # else:
        #     print("Found, skipping write")
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
