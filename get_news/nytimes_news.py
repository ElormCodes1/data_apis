import requests
import json
import re
from proxies import PROXY_LIST
import random
from bs4 import BeautifulSoup
import datetime


urls = ["https://www.nytimes.com/section/business","https://www.nytimes.com/section/technology"]

for url in urls:
    proxy = random.choice(PROXY_LIST)
    proxies = {"http": proxy, "https": proxy}
    response = requests.get(url, proxies=proxies)

    soup = BeautifulSoup(response.text, "lxml")

    # Extract all script tags
    script_tags = [script["src"] if script.has_attr("src") else script for script in soup.find_all("script")]
    data_tag = script_tags[13].get_text()
    data_tag = data_tag.replace("window.__preloadedData = ","").replace('undefined', '"undefined"')[:-1]
    data_tag = json.loads(data_tag)
    # print(data_tag)
    # with open("test.json", "a") as f:
    #     json.dump(data_tag, f)
    # count = 0
    # for key, value in data_tag.get("initialState", {}).items():
    #         if key.startswith("Article:") and isinstance(value, dict) and value.get("__typename") == "Article":
    #             count += 1

    # print(count)

    try:
        initial_state = data_tag.get("initialState", {})
        article_info_list = []
        #  and value.get("__typename") == "Article"
        for key, value in initial_state.items():
            if key.startswith("Article:") and isinstance(value, dict) and value.get("__typename") == "Article":
                # headline_id = value.get("headline", {}).get("id")  # Get the ID of the headline object
                # headline_id = key.split(":")[1]
                # if headline_id and initial_state.get(headline_id): # Check if the headline ID exists and is in initialState
                    # title = initial_state[headline_id].get("default")  # Access the headline object using the ID
                # else:
                        # title = None # or "" or some default value if the headline is missing
                title = value.get("headline").get("default")
                # if title is None:
                #     continue
                pubDate = value.get("firstPublished") or value.get("lastMajorModification")
                # print(type(pubDate))
                # print(datetime.datetime.fromisoformat(pubDate.replace('Z', '+00:00')).strftime("%Y-%m-%d"))
                # if datetime.datetime.fromisoformat(pubDate.replace('Z', '+00:00')).strftime("%Y-%m-%d") != datetime.date.today().strftime("%Y-%m-%d"):
                #      continue
                article_info = {
                    # "url": value.get("url"),
                    "firstPublished": pubDate,
                    "summary": value.get("summary"),
                    "title": title
                }
                article_info_list.append(article_info)

                # print(article_info)
                with open("currnews.txt", "a") as f:
                     f.write(f"{title}\n{value.get("summary")}\n{value.get("firstPublished") or value.get("lastMajorModification")}\n")
                print(f"{title}\n{value.get("summary")}\n{value.get("firstPublished") or value.get("lastMajorModification")}")
                # print("\n")
    except (AttributeError, TypeError):  # Handle JSON decode errors and other potential issues
        print("error")


    # for news in article_info_list:
    #      print(news)