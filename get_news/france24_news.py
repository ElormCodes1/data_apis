import xmltodict
import requests
import json
import datetime



cookies = {
    'ak-inject-mpulse': 'false',
    'didomi_token': 'eyJ1c2VyX2lkIjoiMTk1NTE2YTMtYzYzMC02MTA4LWJhZDctYmZhNGVhZGEwMzE0IiwiY3JlYXRlZCI6IjIwMjUtMDMtMDFUMTE6MTQ6MzEuNjUxWiIsInVwZGF0ZWQiOiIyMDI1LTAzLTAxVDExOjE0OjMyLjE1MVoiLCJ2ZW5kb3JzIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIiwidHdpdHRlciIsImM6c3BvdGlmeS1lbWJlZCIsImM6dmRvcGlhIiwiYzphZHZlcnRpc2luZ2NvbSIsImM6a3J1eC1kaWdpdGFsIiwiYzp5b3V0dWJlIiwiYzpob3RqYXIiLCJjOm5ldy1yZWxpYyIsImM6Y2hhcnRiZWF0IiwiYzpxdWFudHVtLWFkdmVydGlzaW5nIiwiYzpwaW5nZG9tIiwiYzphdWRpZW5jZS1zcXVhcmUiLCJjOmxrcWQiLCJjOm93bnBhZ2UiLCJjOnNvYXN0YS1tcHVsc2UiLCJjOnBvb29sLVZ5aENpdDdOIiwiYzp0aWt0b2stS1pBVVFMWjkiLCJjOmdvb2dsZWFuYS00VFhuSmlnUiIsImM6cGlhbm9oeWJyLVIzVktDMnI0IiwiYzppbnN0YWdyYW0iLCJjOnRlbGVncmFtIiwiYzp0eXBlZm9ybSIsImM6bm9ubGkiLCJjOnN0YXRzLXBlcmZvcm0iLCJjOmFyZW5hIiwiYzp0aHJlYWRzIiwiYzpkaWRvbWkiLCJjOnNvdW5kY2xvdWQiLCJjOnZrb250YWt0ZSIsImM6YmF0Y2giLCJjOmZhY2Vib29rIiwiYzpoNXAiLCJjOmJsdWVza3kiLCJjOmRlZXplciIsImM6Zm1tIl19LCJwdXJwb3NlcyI6eyJlbmFibGVkIjpbImRldmljZV9jaGFyYWN0ZXJpc3RpY3MiLCJnZW9sb2NhdGlvbl9kYXRhIl19LCJ2ZXJzaW9uIjoyLCJhYyI6IkM3ZUFLQUVZQkpZRVNRVTZndTNBLkFBQUEifQ==',
    'euconsent-v2': 'CQNlwwAQNlwwAAHABBENBeFsAP_gAAAAAAqIJvFF_G7eTSFhcWp3YftEOY0ewVA74sAhBgCJA4gBCBpAsJQEkGAIIADAIAAKAAIAIGRBAAFlAADABEAAYIABICDMAAAAIRAAICAAAAABAgBACABIEwAAAAAAgEBUABUAiQIAABogwMBAAAAgBEAAAAAgAIABAAAAACAAQAAQAAAIAggAAAAAAAAAAAAEABAAEAAAAAECAAAAAAAcABAAAAMSgAwABBW8pABgACCt46ADAAEFbyEAGAAIK3hIAMAAQVvLQAYAAgre.f_wAAAAAAAAA',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.7',
    'cache-control': 'max-age=0',
    # 'cookie': 'ak-inject-mpulse=false; didomi_token=eyJ1c2VyX2lkIjoiMTk1NTE2YTMtYzYzMC02MTA4LWJhZDctYmZhNGVhZGEwMzE0IiwiY3JlYXRlZCI6IjIwMjUtMDMtMDFUMTE6MTQ6MzEuNjUxWiIsInVwZGF0ZWQiOiIyMDI1LTAzLTAxVDExOjE0OjMyLjE1MVoiLCJ2ZW5kb3JzIjp7ImVuYWJsZWQiOlsiZ29vZ2xlIiwidHdpdHRlciIsImM6c3BvdGlmeS1lbWJlZCIsImM6dmRvcGlhIiwiYzphZHZlcnRpc2luZ2NvbSIsImM6a3J1eC1kaWdpdGFsIiwiYzp5b3V0dWJlIiwiYzpob3RqYXIiLCJjOm5ldy1yZWxpYyIsImM6Y2hhcnRiZWF0IiwiYzpxdWFudHVtLWFkdmVydGlzaW5nIiwiYzpwaW5nZG9tIiwiYzphdWRpZW5jZS1zcXVhcmUiLCJjOmxrcWQiLCJjOm93bnBhZ2UiLCJjOnNvYXN0YS1tcHVsc2UiLCJjOnBvb29sLVZ5aENpdDdOIiwiYzp0aWt0b2stS1pBVVFMWjkiLCJjOmdvb2dsZWFuYS00VFhuSmlnUiIsImM6cGlhbm9oeWJyLVIzVktDMnI0IiwiYzppbnN0YWdyYW0iLCJjOnRlbGVncmFtIiwiYzp0eXBlZm9ybSIsImM6bm9ubGkiLCJjOnN0YXRzLXBlcmZvcm0iLCJjOmFyZW5hIiwiYzp0aHJlYWRzIiwiYzpkaWRvbWkiLCJjOnNvdW5kY2xvdWQiLCJjOnZrb250YWt0ZSIsImM6YmF0Y2giLCJjOmZhY2Vib29rIiwiYzpoNXAiLCJjOmJsdWVza3kiLCJjOmRlZXplciIsImM6Zm1tIl19LCJwdXJwb3NlcyI6eyJlbmFibGVkIjpbImRldmljZV9jaGFyYWN0ZXJpc3RpY3MiLCJnZW9sb2NhdGlvbl9kYXRhIl19LCJ2ZXJzaW9uIjoyLCJhYyI6IkM3ZUFLQUVZQkpZRVNRVTZndTNBLkFBQUEifQ==; euconsent-v2=CQNlwwAQNlwwAAHABBENBeFsAP_gAAAAAAqIJvFF_G7eTSFhcWp3YftEOY0ewVA74sAhBgCJA4gBCBpAsJQEkGAIIADAIAAKAAIAIGRBAAFlAADABEAAYIABICDMAAAAIRAAICAAAAABAgBACABIEwAAAAAAgEBUABUAiQIAABogwMBAAAAgBEAAAAAgAIABAAAAACAAQAAQAAAIAggAAAAAAAAAAAAEABAAEAAAAAECAAAAAAAcABAAAAMSgAwABBW8pABgACCt46ADAAEFbyEAGAAIK3hIAMAAQVvLQAYAAgre.f_wAAAAAAAAA',
    'priority': 'u=0, i',
    'referer': 'https://www.france24.com/en/rss-feeds',
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
    return xmltodict.parse(response.content, process_namespaces=True, cdata_key='#text')

with open("news.json", "r") as f:
             ns = f.readlines()

# def saveRSS(filepath: str, data: dict) -> None:
#     with open(filepath, 'w') as file:
#         json.dump(data, file, indent=4)
#  "https://www.france24.com/en/europe/rss", "https://www.france24.com/en/asia-pacific/rss",
urls = ["https://www.france24.com/en/rss", "https://www.france24.com/en/business-tech/rss"]
for url in urls:
    data = getRSS(url)

    # saveRSS("database\\rss_feed_0.json", data)

    # now read the news from the saved file
    # with open("database\\rss_feed_0.json", 'r') as file:
        # data = json.load(file)
        
    for item in data['rss']['channel']['item']:
        if datetime.datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S GMT").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
             continue
        print(f"{item['title']}\n{item['description']}\n{item["pubDate"]}")
        # print(item['link'])
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
        # with open("news.json", "a") as f:
        #      json.dump(fndata, f)
        #      f.write("\n")
        # with open("currnews.txt", "a") as f:
        #         f.write(f"{item['title']}\n{item['description']}\n{item["pubDate"]}\n")
        # print()
