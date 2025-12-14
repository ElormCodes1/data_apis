import requests
import json
import datetime

cookies = {
    'at_check': 'true',
    'ab_nav_threshold_variable_4': '48',
    'LaunchDarklyUser': '1669c810-f6a6-11ef-9924-6f64e522de3c',
    '__sp': 'private_investor%3D-web_share%3D-web_index%3D-token%3D',
    '__losp': 'web_share%3D2-web_index%3D2',
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.6',
    # 'cookie': 'at_check=true; ab_nav_threshold_variable_4=48; LaunchDarklyUser=1669c810-f6a6-11ef-9924-6f64e522de3c; __sp=private_investor%3D-web_share%3D-web_index%3D-token%3D; __losp=web_share%3D2-web_index%3D2',
    'priority': 'u=1, i',
    'referer': 'https://www.hl.co.uk/shares/stock-market-news/company--news',
    'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
}

with open("news.json", "r") as f:
             ns = f.readlines()

params = {
    'page': '1',
    'id': '31951',
}

response = requests.get('https://www.hl.co.uk/ajax/article-listings/sharecast', params=params, cookies=cookies, headers=headers)
data = response.json()

for news in data["results"]:
    title = news["name"]
    url = news["url"]
    description = news["intro"]
    date = news["publish_date"]
    # print(type(date))
    # if datetime.datetime.strptime(date, "%a, %d %B %Y %H:%M").strftime("%d %b %Y") != datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y"):
    #         continue
    print(f"{title}\n{description}\n{date}")
    # print(item['link'])
    fndata = {
             "title": title,
             "description": description,
             "date": date
        }
    # with open("news.json", "a") as f:
    #         json.dump(fndata, f)
    #         f.write("\n")
    # with open("currnews.txt", "a") as f:
    #         f.write(f"{title}\n{description}\n{date}\n")
    # print()
    fndata_str = json.dumps(fndata).strip()

    # Check if `fndata_str` exists in `ns`
    if not ns or not any(fndata_str == line.strip() for line in ns):
        with open("news.json", "a") as f:
            json.dump(fndata, f)
            f.write("\n")

        with open("newsforanalysis.txt", "a") as f:
            f.write(f"{title}\n{description}\n{date}\n")
    else:
        print("Found, skipping write")
    # print(title)