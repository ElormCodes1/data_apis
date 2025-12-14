import xmltodict
import requests
import json
import datetime
from proxies import PROXY_LIST
from dotenv import load_dotenv
import random

cookies = {
    'region': 'WORLD',
    '_pctx': '%7Bu%7DN4IgrgzgpgThIC4B2YA2qA05owMoBcBDfSREQpAeyRCwgEt8oBJAEzIEYOAWABgA4AzPwBMg7iP68A7LwHSAnCAC%2BQA',
    '_pcid': '%7B%22browserId%22%3A%22m8jbutwuli5f16pq%22%7D',
    'adops_master_kvs': '',
    '__pat': '-14400000',
    'client_type': 'html5',
    'client_version': '4.7.1',
    'BI_UI_RVAffiliateDocID': '10001147',
    '__pvi': 'eyJpZCI6InYtbThqYnV0d3piZTgxNjY1YiIsImRvbWFpbiI6Ii5jbmJjLmNvbSIsInRpbWUiOjE3NDI1OTUwODUxOTd9',
    '__tbc': '%7Bkpex%7Dm3TdWoPSMPRJmUos_pYlgaWLpZ1UDJDDg8JMTchc8tDJsfCktGHQ5oSCzxVt1YIE',
    'xbc': '%7Bkpex%7DxmPqcO6e_QwR4ZHZenSjoQ',
    'sailthru_pageviews': '3',
    'AWSALB': '5UVS6J5SIMjomDXH2V5gwr8J2yFlAo9LfzpTcFynYA/+3XO6YE/YAD+uXh76fnDsr6P0zUAyc7eRq9Y8CKddWMNy1qYYZFe6tC71ZTtsZKOnZxehdr+0fRb+24Wi',
    'AWSALBCORS': '5UVS6J5SIMjomDXH2V5gwr8J2yFlAo9LfzpTcFynYA/+3XO6YE/YAD+uXh76fnDsr6P0zUAyc7eRq9Y8CKddWMNy1qYYZFe6tC71ZTtsZKOnZxehdr+0fRb+24Wi',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.8',
    'cache-control': 'max-age=0',
    'if-modified-since': 'Fri, 21 Mar 2025 22:00:37 GMT',
    'if-none-match': 'W/"15a6c-630e1627386e0"',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Brave";v="134"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'cross-site',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    # 'cookie': 'region=WORLD; _pctx=%7Bu%7DN4IgrgzgpgThIC4B2YA2qA05owMoBcBDfSREQpAeyRCwgEt8oBJAEzIEYOAWABgA4AzPwBMg7iP68A7LwHSAnCAC%2BQA; _pcid=%7B%22browserId%22%3A%22m8jbutwuli5f16pq%22%7D; adops_master_kvs=; __pat=-14400000; client_type=html5; client_version=4.7.1; BI_UI_RVAffiliateDocID=10001147; __pvi=eyJpZCI6InYtbThqYnV0d3piZTgxNjY1YiIsImRvbWFpbiI6Ii5jbmJjLmNvbSIsInRpbWUiOjE3NDI1OTUwODUxOTd9; __tbc=%7Bkpex%7Dm3TdWoPSMPRJmUos_pYlgaWLpZ1UDJDDg8JMTchc8tDJsfCktGHQ5oSCzxVt1YIE; xbc=%7Bkpex%7DxmPqcO6e_QwR4ZHZenSjoQ; sailthru_pageviews=3; AWSALB=5UVS6J5SIMjomDXH2V5gwr8J2yFlAo9LfzpTcFynYA/+3XO6YE/YAD+uXh76fnDsr6P0zUAyc7eRq9Y8CKddWMNy1qYYZFe6tC71ZTtsZKOnZxehdr+0fRb+24Wi; AWSALBCORS=5UVS6J5SIMjomDXH2V5gwr8J2yFlAo9LfzpTcFynYA/+3XO6YE/YAD+uXh76fnDsr6P0zUAyc7eRq9Y8CKddWMNy1qYYZFe6tC71ZTtsZKOnZxehdr+0fRb+24Wi',
}

def getRSS(url: str) -> dict:
    response = requests.get(url, headers=headers, proxies={"http": random.choice(PROXY_LIST)})
    return xmltodict.parse(response.content)

with open("news.json", "r") as f:
             ns = f.readlines()
# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)

urls = ["https://www.cnbc.com/sitemap_news.xml"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['urlset']['url']:
        if datetime.datetime.strptime((item["n:news"]["n:publication_date"])[:-6], "%Y-%m-%dT%H:%M:%S").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
             continue
        # print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
        # print(item['link'])
        fndata = {
             "title": item["n:news"]['n:title'],
            #  "description": item['description'],
             "date": item["n:news"]["n:publication_date"]
        }
        # Convert `fndata` to a string for comparison
        fndata_str = json.dumps(fndata).strip()

        # Check if `fndata_str` exists in `ns`
        if not ns or not any(fndata_str == line.strip() for line in ns):
            with open("news.json", "a") as f:
                json.dump(fndata, f)
                f.write("\n")

            with open("newsforanalysis.txt", "a") as f:
                f.write(f"{item["n:news"]['n:title']}\n{item["n:news"]["n:publication_date"]}\n")
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
