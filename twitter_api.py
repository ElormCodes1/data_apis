"""
Twitter Scraper API

FastAPI router for Twitter data scraping functionality.
Includes profile information, followers, following, posts, and search capabilities.
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import requests
import json
from bs4 import BeautifulSoup
import logging
import time
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor
from curl_cffi import requests as curl_requests
from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv

load_dotenv()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create router instead of app
router = APIRouter()

# In-memory storage for background tasks
tasks: Dict[str, Dict[str, Any]] = {}

# Pydantic models for task management
class ListMembersStatus(BaseModel):
    """List members task status model"""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int  # 0-100
    message: str
    list_id: str
    total_members: int = 0
    pages_processed: int = 0
    current_page: int = 0
    last_updated: str
    results: List[Dict[str, Any]] = []  # Store the extracted members

# @router.get("/")
# async def root():
#     return {"message": "Twitter API"}

# @router.get("/profile_info")
# async def profile_info(username: str = Query(..., description="account username")):
#     cookies = {
#         'guest_id': '173823245631103789',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/NanouuSymeon',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }
#     username = username or "nanouusymeon"
#     variables = {"screen_name":username}

#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
#         'fieldToggles': '{"withAuxiliaryUserLabels":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )
#     # print(response.json())
#     if not response.json()["data"]:  # Check if "data" is empty
#         raise HTTPException(status_code=400, detail="No data available for this profile")

#     user_id = response.json()["data"]["user"]["result"]["rest_id"]
#     name = response.json()["data"]["user"]["result"]["legacy"]["name"]
#     description = response.json()["data"]["user"]["result"]["legacy"]["description"]
#     followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
#     following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]

#     data = {
#         "name": name,
#         "description": description,
#         "followers_count": followers,
#         "following_count": following
#     }
#     print(data)
#     return data

# @router.get("/followers")
# async def get_followers(username: str = Query(..., description="account username")):
#     followers_list = []
#     cookies = {
#         'guest_id': '173823245631103789',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/NanouuSymeon',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }
#     username = username or "nanouusymeon"
#     variables = {"screen_name":username}

#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
#         'fieldToggles': '{"withAuxiliaryUserLabels":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )

#     user_id = response.json()["data"]["user"]["result"]["rest_id"]
#     name = response.json()["data"]["user"]["result"]["legacy"]["name"]
#     description = response.json()["data"]["user"]["result"]["legacy"]["description"]
#     followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
#     following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]

#     print({
#         "name": name,
#         "description": description,
#         "followers_count": followers,
#         "following_count": following
#     })
#     variables = {
#         "userId": user_id,
#         "count": 1000,
#         "includePromotedContent": True,
#         "withQuickPromoteEligibilityTweetFields": True,
#         "withVoice": True,
#         "withV2Timeline": True
#     }


#     params = {
#         "variables": json.dumps(variables),
#         "features": '{"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"articles_preview_enabled":false,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"tweet_with_visibility_results_prefer_gql_media_interstitial_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}',
#     }

#     response = requests.get(
#         "https://twitter.com/i/api/graphql/ZxuX4tC6kWz9M8pe1i-Gdg/Following",
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )

#     # json_data = json.loads(response.text)

#     data = json.loads(response.text)
#     # print(data)
#     # Extract instructions from the JSON data
#     instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
#     for instruction in instructions:
#         if instruction["type"] == "TimelineAddEntries":
#             # Extract the entries from the instruction
#             entries = instruction["entries"]
#             # Loop through each entry and extract required information
#             for entry in entries:
#                 content = entry["content"]
#                 try:
#                     user_result = content["itemContent"]["user_results"]["result"]
#                 except:
#                     continue
#                 name = user_result["legacy"]["name"]
#                 followers_count = user_result["legacy"]["followers_count"]
#                 friends_count = user_result["legacy"]["friends_count"]
#                 description = user_result["legacy"]["description"]
#                 username = user_result["legacy"]["screen_name"]
#                 # Print extracted information
#                 # print(f"Name: {name}")
#                 # print(f"Followers: {followers_count}")
#                 # print(f"Following: {friends_count}")
#                 # print("-------------------------")
#                 full_data = {
#                     "follower_name": name,
#                     "followers_count": followers_count,
#                     "following_count": friends_count,
#                     "description": description,
#                     "username": username,
#                     "profile_url": f"https://x.com/{username}"
#                 }
#                 followers_list.append(full_data)
#                 # print(full_data)
#     cookies = {
#         'guest_id': '173823245631103789',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/rupali_codes/verified_followers',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'SsWXliwJSClRZEd8MLKgnKPyXtadv+O1YfUoJhlNFOv/TadC3uw/OJComNh88EB0BdUrPUloewEMEEDeT5XwepX0ijvnSQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }

#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/WijS8Cwfqhtk5hDN9q7sgw/BlueVerifiedFollowers',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )
#     data = json.loads(response.text)
#     # print(data)
#     # Extract instructions from the JSON data
#     instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
#     for instruction in instructions:
#         if instruction["type"] == "TimelineAddEntries":
#             # Extract the entries from the instruction
#             entries = instruction["entries"]
#             # Loop through each entry and extract required information
#             for entry in entries:
#                 content = entry["content"]
#                 try:
#                     user_result = content["itemContent"]["user_results"]["result"]
#                 except:
#                     continue
#                 name = user_result["legacy"]["name"]
#                 followers_count = user_result["legacy"]["followers_count"]
#                 friends_count = user_result["legacy"]["friends_count"]
#                 description = user_result["legacy"]["description"]
#                 username = user_result["legacy"]["screen_name"]
#                 full_data = {
#                     "follower_name": name,
#                     "followers_count": followers_count,
#                     "following_count": friends_count,
#                     "description": description,
#                     "username": username,
#                     "profile_url": f"https://x.com/{username}"
#                 }
#                 followers_list.append(full_data)
#                 # print(full_data)
#     print(followers_list)
#     print(len(followers_list))
#     return followers_list


# @router.get("/following")
# async def get_following(username: str = Query(..., description="account username")):
#     following_list = []
#     cookies = {
#         'guest_id': '173823245631103789',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/NanouuSymeon',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }
#     username = username or "nanouusymeon"
#     variables = {"screen_name":username}

#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
#         'fieldToggles': '{"withAuxiliaryUserLabels":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )

#     user_id = response.json()["data"]["user"]["result"]["rest_id"]
#     name = response.json()["data"]["user"]["result"]["legacy"]["name"]
#     description = response.json()["data"]["user"]["result"]["legacy"]["description"]
#     followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
#     following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]

#     print({
#         "name": name,
#         "description": description,
#         "followers_count": followers,
#         "following_count": following
#     })

#     cookies = {
#         'guest_id': '173823245631103789',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/NanouuSymeon/following',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'K6T2901oKUgwBSYdUdPB/cKTP7f83oLUAJRJR3gsdYqeLMYjv41eWfHJ+bkdkSEVZANZXCjryv+TtCozg0cw7MLZidmRKA',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }

#     variables = {"userId":user_id,"count":1000,"includePromotedContent":False}

#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/o5eNLkJb03ayTQa97Cpp7w/Following',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )

#     data = json.loads(response.text)
#     # print(data)
#     # Extract instructions from the JSON data
#     instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
#     for instruction in instructions:
#         if instruction["type"] == "TimelineAddEntries":
#             # Extract the entries from the instruction
#             entries = instruction["entries"]
#             # Loop through each entry and extract required information
#             for entry in entries:
#                 content = entry["content"]
#                 try:
#                     user_result = content["itemContent"]["user_results"]["result"]
#                 except:
#                     continue
#                 name = user_result["legacy"]["name"]
#                 followers_count = user_result["legacy"]["followers_count"]
#                 friends_count = user_result["legacy"]["friends_count"]
#                 description = user_result["legacy"]["description"]
#                 username = user_result["legacy"]["screen_name"]
#                 full_data = {
#                     "follower_name": name,
#                     "followers_count": followers_count,
#                     "following_count": friends_count,
#                     "description": description,
#                     "username": username,
#                     "profile_url": f"https://x.com/{username}"
#                 }
#                 following_list.append(full_data)
#                 # print(full_data)
#     print(following_list)
#     print(len(following_list))
#     return following_list


# @router.get("/posts")
# async def get_profile_posts(username: str = Query(..., description="account username")):
#     posts_list = []
#     cookies = {
#         'guest_id': '173823245631103789',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/NanouuSymeon',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }
#     username = username or "nanouusymeon"
#     variables = {"screen_name":username}

#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
#         'fieldToggles': '{"withAuxiliaryUserLabels":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )

#     user_id = response.json()["data"]["user"]["result"]["rest_id"]
#     name = response.json()["data"]["user"]["result"]["legacy"]["name"]
#     description = response.json()["data"]["user"]["result"]["legacy"]["description"]
#     followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
#     following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]

#     print({
#         "name": name,
#         "description": description,
#         "followers_count": followers,
#         "following_count": following
#     })



#     variables = {
#         "userId": user_id,
#         "count": 100,
#         "includePromotedContent": True,
#         "withQuickPromoteEligibilityTweetFields": True,
#         "withVoice": True,
#         "withV2Timeline": True
#     }


#     params = {
#         'variables': json.dumps(variables),
#         'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
#         'fieldToggles': '{"withArticlePlainText":false}',
#     }

#     response = requests.get(
#         'https://x.com/i/api/graphql/Y9WM4Id6UcGFE8Z-hbnixw/UserTweets',
#         params=params,
#         cookies=cookies,
#         headers=headers,
#     )


#     posts = response.json()
#     try:
#         posts = posts["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"][2]["entries"]
#     except:
#         posts = posts["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"][1]["entries"]
#     print(len(posts))
#     # with open("testc.json", "w") as f:
#     #     json.dump(posts, f)

#     for entries in posts:
#             post_url = f'https://x.com/{username}/status/{(entries["entryId"].split("-"))[1]}'
#             # post_url = entries["entryId"]
#             try:
#                 entriess = entries["content"]["items"]
#                 # print(len(entriess))
#             except:
#                 entriess = []
#                 # print(f"len of entriesss {len(entriess)}")
#                 # print(len(entriess)==0)
#             if len(entriess) == 0:
#                 try:
#                     views = entries["content"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
#                 except:
#                     views = None
#                 try:
#                     bookmarks = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
#                 except:
#                     bookmarks = None
#                 try:
#                     tweet_date = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
#                 except:
#                     tweet_date = None
#                 if tweet_date is None:
#                     continue
#                 try:
#                     media_type = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
#                 except:
#                     media_type = None
#                 try:
#                     likes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
#                 except:
#                     likes =None
#                 try:
#                     tweet_text = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
#                     if "RT @" in tweet_text:
#                         isretweet = True
#                     else:
#                         isretweet = False
#                 except:
#                     tweet_text = None
#                 try:
#                     quotes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
#                 except:
#                     quotes = None
#                 try:
#                     replies = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
#                 except:
#                     replies = None
#                 try:
#                     retweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
#                 except:
#                     retweet =  None
#                 try:
#                     quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
#                 except:
#                     quoted_tweet = None
#                 try:
#                     url = post_url
#                 except:
#                     url = None

#                 data = {
#                     "views": views,
#                     "bookmarks": bookmarks,
#                     "tweet_date": tweet_date,
#                     "media_type": media_type,
#                     "likes": likes,
#                     "tweet_text": tweet_text,
#                     "quotes": quotes,
#                     "replies": replies,
#                     "retweetc": retweet,
#                     "thread_tweet": False,
#                     "quoted_tweet": quoted_tweet,
#                     "isRetweet": isretweet,
#                     "url": url
#                 }
#                 posts_list.append(data)
#                 print(data)
                
#             else:
#                 for entry in entriess:
#                     try:
#                         views = entry["item"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
#                     except:
#                         views = None
#                     try:
#                         bookmarks = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
#                     except:
#                         bookmarks = None
#                     try:
#                         tweet_date = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
#                     except:
#                         tweet_date = None
#                     if tweet_date is None:
#                         continue
#                     try:
#                         media_type = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
#                     except:
#                         media_type = None
#                     try:
#                         likes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
#                     except:
#                         likes =None
#                     try:
#                         tweet_text = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
#                         if "RT @" in tweet_text:
#                             isretweet = True
#                         else:
#                             isretweet = False
#                     except:
#                         tweet_text = None
#                     try:
#                         quotes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
#                     except:
#                         quotes = None
#                     try:
#                         replies = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
#                     except:
#                         replies = None
#                     try:
#                         retweet = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
#                     except:
#                         retweet =  None
#                     try:
#                         quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
#                     except:
#                         quoted_tweet = None
                    
#                     data = {
#                         "views": views,
#                         "bookmarks": bookmarks,
#                         "tweet_date": tweet_date,
#                         "media_type": media_type,
#                         "likes": likes,
#                         "tweet_text": tweet_text,
#                         "quotes": quotes,
#                         "replies": replies,
#                         "retweetc": retweet,
#                         "quoted_tweet": quoted_tweet,
#                         "thread_tweet": True,
#                         "isRetweet": isretweet,
#                         "url": url
#                     }
#                     posts_list.append(data)
#                     print(data)
#     return posts_list


# @router.get("/search")
# async def search_tweets(query: str = Query(..., description="search query")):
#     cookies = {
#         'guest_id': 'v1%3A171353782335253191',
#         'twid': 'u%3D1663936852208898049',
#         'auth_token': 'b27ab02b6fbcf00d1db8e7bf1a319d973084924b',
#         'guest_id_ads': 'v1%3A171353782335253191',
#         'guest_id_marketing': 'v1%3A171353782335253191',
#         'ct0': '52d09056b351acee0d101bbf7949c3f45be213602e00f6241942e4b963a61e471032b0d0db10318ac97d8b6c5c302bb4936c21d8dd39f3ef0ed3d1e3467c2fd79b1e34ee44fdbcd8510bf5a82f158376',
#         'lang': 'en',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'personalization_id': '"v1_WUjf0NUgaPWRX4efQJqAqA=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.5',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com',
#         'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'g7kus5wNnyIeKG8Dn68Bv5stgeTu4k4VYskkPw21zMuc1oE59rpwZrX4YtAHV3HIL5sZroC7n1uryGd3nqsgM0/KLnK7gA',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '52d09056b351acee0d101bbf7949c3f45be213602e00f6241942e4b963a61e471032b0d0db10318ac97d8b6c5c302bb4936c21d8dd39f3ef0ed3d1e3467c2fd79b1e34ee44fdbcd8510bf5a82f158376',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }

#     url = f'https://x.com/i/api/graphql/BkkaU7QQGQBGnYgk4pKh4g/SearchTimeline'
#     variables = {
#         "rawQuery": query,
#         "count": 100,
#         "querySource": "typed_query",
#         "product": "Top"
#     }
#     features = {
#         "responsive_web_grok_share_attachment_enabled": False,
#         "freedom_of_speech_not_reach_fetch_enabled": True,
#         "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
#         "responsive_web_twitter_article_tweet_consumption_enabled": True,
#         "rweb_tipjar_consumption_enabled": True,
#         "profile_label_improvements_pcf_label_in_post_enabled": False,
#         "longform_notetweets_rich_text_read_enabled": True,
#         "standardized_nudges_misinfo": True,
#         "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
#         "responsive_web_grok_analyze_post_followups_enabled": True,
#         "premium_content_api_read_enabled": False,
#         "rweb_video_timestamps_enabled": True,
#         "responsive_web_enhance_cards_enabled": False,
#         "longform_notetweets_inline_media_enabled": True,
#         "communities_web_enable_tweet_community_results_fetch": True,
#         "verified_phone_label_enabled": False,
#         "creator_subscriptions_tweet_preview_api_enabled": True,
#         "c9s_tweet_anatomy_moderator_badge_enabled": True,
#         "responsive_web_edit_tweet_api_enabled": True,
#         "view_counts_everywhere_api_enabled": True,
#         "tweet_awards_web_tipping_enabled": False,
#         "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
#         "articles_preview_enabled": True,
#         "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
#         "creator_subscriptions_quote_tweet_preview_enabled": False,
#         "longform_notetweets_consumption_enabled": True,
#         "responsive_web_graphql_exclude_directive_enabled": True,
#         "responsive_web_graphql_timeline_navigation_enabled": True,
#     }
#     params = {
#         'variables': json.dumps(variables),
#         'features': json.dumps(features),
#     }

#     response = requests.get(url, cookies=cookies, headers=headers, params=params)
#     data = response.json()
#     # with open("test.json", "w") as f:
#     #     json.dump(data, f)
#     print(data)

#     try:
#         posts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][0]["entries"]
#     except:
#         posts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][1]["entries"]

#     # print(posts)

#     # with open('twitter_content.json', 'w') as f:
#     #     json.dump(posts, f)

#     posts_list = []

#     for entries in posts:
#             if "tweet-" not in entries["entryId"]:
#                         continue
#             else:
#                 # post_url = entries["entryId"]
#                 try:
#                     entriess = entries["content"]["items"]
#                     # print(len(entriess))
#                 except:
#                     entriess = []
#                     # print(f"len of entriesss {len(entriess)}")
#                     # print(len(entriess)==0)
#                 if len(entriess) == 0:
#                     username = entries["content"]["itemContent"]["tweet_results"]["result"]["core"]["user_results"]["result"]["legacy"]["screen_name"]
#                     post_url = f'https://x.com/{username}/status/{(entries["entryId"].split("-"))[1]}'
#                     try:
#                         views = entries["content"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
#                     except:
#                         views = None
#                     try:
#                         bookmarks = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
#                     except:
#                         bookmarks = None
#                     try:
#                         tweet_date = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
#                     except:
#                         tweet_date = None
#                     if tweet_date is None:
#                         continue
#                     try:
#                         media_type = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
#                     except:
#                         media_type = None
#                     try:
#                         likes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
#                     except:
#                         likes =None
#                     try:
#                         tweet_text = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
#                         if "RT @" in tweet_text:
#                             isretweet = True
#                         else:
#                             isretweet = False
#                     except:
#                         tweet_text = None
#                     try:
#                         quotes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
#                     except:
#                         quotes = None
#                     try:
#                         replies = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
#                     except:
#                         replies = None
#                     try:
#                         retweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
#                     except:
#                         retweet =  None
#                     try:
#                         quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
#                     except:
#                         quoted_tweet = None
#                     try:
#                         url = post_url
#                     except:
#                         url = None

#                     data = {
#                         "views": views,
#                         "bookmarks": bookmarks,
#                         "tweet_date": tweet_date,
#                         "media_type": media_type,
#                         "likes": likes,
#                         "tweet_text": tweet_text,
#                         "quotes": quotes,
#                         "replies": replies,
#                         "retweetc": retweet,
#                         "thread_tweet": False,
#                         "quoted_tweet": quoted_tweet,
#                         "isRetweet": isretweet,
#                         "url": url
#                     }
#                     posts_list.append(data)
#                     print(data)

#                 else:
#                     for entry in entriess:
#                         username = entry["item"]["itemContent"]["tweet_results"]["result"]["core"]["user_results"]["result"]["legacy"]["screen_name"]
#                         post_url = f'https://x.com/{username}/status/{(entries["entryId"].split("-"))[1]}'
#                         try:
#                             views = entry["item"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
#                         except:
#                             views = None
#                         try:
#                             bookmarks = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
#                         except:
#                             bookmarks = None
#                         try:
#                             tweet_date = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
#                         except:
#                             tweet_date = None
#                         if tweet_date is None:
#                             continue
#                         try:
#                             media_type = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
#                         except:
#                             media_type = None
#                         try:
#                             likes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
#                         except:
#                             likes =None
#                         try:
#                             tweet_text = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
#                             if "RT @" in tweet_text:
#                                 isretweet = True
#                             else:
#                                 isretweet = False
#                         except:
#                             tweet_text = None
#                         try:
#                             quotes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
#                         except:
#                             quotes = None
#                         try:
#                             replies = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
#                         except:
#                             replies = None
#                         try:
#                             retweet = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
#                         except:
#                             retweet =  None
#                         try:
#                             quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
#                         except:
#                             quoted_tweet = None
#                         try:
#                             url = post_url
#                         except:
#                             url = None
                        
#                         data = {
#                             "views": views,
#                             "bookmarks": bookmarks,
#                             "tweet_date": tweet_date,
#                             "media_type": media_type,
#                             "likes": likes,
#                             "tweet_text": tweet_text,
#                             "quotes": quotes,
#                             "replies": replies,
#                             "retweetc": retweet,
#                             "quoted_tweet": quoted_tweet,
#                             "thread_tweet": True,
#                             "isRetweet": isretweet,
#                             "url": url
#                         }
#                         posts_list.append(data)
#                         print(data)
#     return posts_list


# @router.get("/search_people")
# async def search_people(query: str = Query(..., description="search query")):
#     account_res = []
#     cookies = {
#         'guest_id': '173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/search?q=(%22AI%20agent%22%20OR%20%22open%20source%22%20OR%20%22LLM%22%20OR%20%22Large%20language%20model%22%20OR%20%22Agentic%22)%20-is%3Aretweet%20lang%3Aen%20since%3A2024-12-30%20until%3A2024-12-31%20min_faves%3A50%20min_retweets%3A10%20-filter%3Areplies&src=typed_query&f=user',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'gikStOe1Fv43ifqYbVglRNp5ibfykFnAe4T4n+v6egcfYHiT1yafobsRZAeRuHFIEWR49YFyOtA6jkiRvJcHarnVKB2LgQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }
#     search_query = query

#     # Define the GraphQL variables
#     graphql_variables = {
#         "rawQuery": search_query,
#         "count": 100,
#         "querySource": "typed_query",
#         "product": "People",
#     }

#     # Define the feature flags
#     features = {
#         "profile_label_improvements_pcf_label_in_post_enabled": True,
#         "rweb_tipjar_consumption_enabled": True,
#         "responsive_web_graphql_exclude_directive_enabled": True,
#         "verified_phone_label_enabled": False,
#         "creator_subscriptions_tweet_preview_api_enabled": True,
#         "responsive_web_graphql_timeline_navigation_enabled": True,
#         "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
#         "premium_content_api_read_enabled": False,
#         "communities_web_enable_tweet_community_results_fetch": True,
#         "c9s_tweet_anatomy_moderator_badge_enabled": True,
#         "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
#         "responsive_web_grok_analyze_post_followups_enabled": True,
#         "responsive_web_jetfuel_frame": False,
#         "responsive_web_grok_share_attachment_enabled": True,
#         "articles_preview_enabled": True,
#         "responsive_web_edit_tweet_api_enabled": True,
#         "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
#         "view_counts_everywhere_api_enabled": True,
#         "longform_notetweets_consumption_enabled": True,
#         "responsive_web_twitter_article_tweet_consumption_enabled": True,
#         "tweet_awards_web_tipping_enabled": False,
#         "responsive_web_grok_analysis_button_from_backend": True,
#         "creator_subscriptions_quote_tweet_preview_enabled": False,
#         "freedom_of_speech_not_reach_fetch_enabled": True,
#         "standardized_nudges_misinfo": True,
#         "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
#         "rweb_video_timestamps_enabled": True,
#         "longform_notetweets_rich_text_read_enabled": True,
#         "longform_notetweets_inline_media_enabled": True,
#         "responsive_web_grok_image_annotation_enabled": False,
#         "responsive_web_enhance_cards_enabled": False,
#     }

#     # Construct the request URL
#     base_url = "https://x.com/i/api/graphql/U3QTLwGF8sZCHDuWIMSAmg/SearchTimeline"
#     params = {
#         "variables": json.dumps(graphql_variables),
#         "features": json.dumps(features),
#     }

#     # Make the request
#     response = requests.get(base_url, cookies=cookies, headers=headers, params=params)
#     # print(response.json())
#     accounts = response.json()["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][1]["entries"]
#     # with open("test.json", "w") as f:
#     #     json.dump(accounts, f)
#     for account in accounts:
#         try:
#             username = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["screen_name"]
#             # print(username)
#             account_url = f'https://x.com/{username}/'
#             name = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["name"]
#             description = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["description"]
#             followers = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["followers_count"]
#             following = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["friends_count"]

#             data = {
#                 "name": name,
#                 "description": description,
#                 "followers_count": followers,
#                 "following_count": following,
#                 "url": account_url
#             }
#             account_res.append(data)
#         except:
#             continue
#     return account_res



# # @router.get("/google_scholar_search")
# # async def search_google_scholar(query: str = Query(..., description="researcher name")):
# #     cookies = {
# #         'SID': 'g.a000ugj-fQTzuxvWidXhAAwQMZcq0mXjrAYe9uoPC-ldxQYUMSWRyDuuX3YbJiZFRqJb9x2l2wACgYKAXISARUSFQHGX2MiqoAozUvlevPy-b21k5XMZxoVAUF8yKo9-qL_kO2PH27rgr310gxj0076',
# #         '__Secure-1PSID': 'g.a000ugj-fQTzuxvWidXhAAwQMZcq0mXjrAYe9uoPC-ldxQYUMSWRo7NLBWJnSL6K2aSEXdP30AACgYKAV0SARUSFQHGX2Mi2WMajMCdQwEQFPhz5PPEPxoVAUF8yKqRMphI0aM3c13mAX6Fec_C0076',
# #         '__Secure-3PSID': 'g.a000ugj-fQTzuxvWidXhAAwQMZcq0mXjrAYe9uoPC-ldxQYUMSWRl1MhhtJrZ_svTlILE0xMGQACgYKAd0SARUSFQHGX2MioO_qP9PBVTU3bg5JWUEFmRoVAUF8yKrZ4okcOqvHXwE9uuLNjrn70076',
# #         'HSID': 'AV6j6nf_VJIj9H0qc',
# #         'SSID': 'AXGz_rZeeFAVHZVgz',
# #         'APISID': '5vRTL5l6zaYUWoz6/AtcDLtuyXorP6EeZl',
# #         'SAPISID': 'kB_MF2GliJ38pBd_/A2J3geXvHmBshpuij',
# #         '__Secure-1PAPISID': 'kB_MF2GliJ38pBd_/A2J3geXvHmBshpuij',
# #         '__Secure-3PAPISID': 'kB_MF2GliJ38pBd_/A2J3geXvHmBshpuij',
# #         'GSP': 'LM=1741362553:S=CtcxX1EH3-0bWK3p',
# #         'AEC': 'AVcja2dvTNm_SyYVTLgByG8nHnSmAIHq5LP8cko9mBIIEkCAnECOryDzMnQ',
# #         'NID': '522=I9-XZucWBQ4eceUYq5-KsaiidEeol2HwFxlYUlrha3-WXU-BreP2LvReCh8-gVI6N75HZJmchizAP4T2S-e5jujfkvCGqlY0_jhjcDMZOxWYwHDc167m9WVStJ6mZLW6w-IdPb6uwIIqq4KMxA3SqS5aX4NPi6F7UDdSrqypgfXrRka-KxFhER73eMJTKr-Jd1xzuDwH62xSsgMjQN7pqEBAeVbwbvpn1b5gFD5ocVDxuiHOxBv2K8FePZV7V5KRlPQ0MvNaWxEsoNMbYU5gbadl3ptlxURe7f-Q4NWeMc8oL75DvnR-eGdB-uzK4Omv1Qfz4c7dnaG9c4w9p4LyrnrVvyjOrZu6KZnpKCDxVV0nENHmzdo2J3WmfOODELtwBBiKOuvVASIKwdJEAiI58fxUgkxWFn3UyaPTNxqbe8RbJABrMjaYvE8qhZVJ6cvap-i0lXJu8i5Ucrp7EYNDyli1Kr87FApOp1qln4ML8_oGFK148Uj52-YxnZizTas59XNCnzPFyCAX-WIckquWaLWQ3JdFlS4LafBBmK7P7Z6ClXhb7TiqyQXfBU20nsccG83elZaajFWBuT2hdeS5C0nwCpEFl_IM4D7r6NFfQiPvWBQiz0I0FSFY347QPkRB-FLo61ekA1ZuDFYVcTHPmzExjJe1RJwG14x0UMobj6DzVM-fv2OzJy6aRiLvuW9V3TqOTEiAkUAgHcDaY3ji8S4b4xNkjAzLJzll9XVskJ3BvF6W5e__aejE5XWZAY3LPg',
# #         '__Secure-1PSIDTS': 'sidts-CjIBEJ3XV_fuko41vlUSKjr0XjqiKLQMB-rg7u0XmSt3Qqi1F4P1U5MQz4h8lcs-5n5-LBAA',
# #         '__Secure-3PSIDTS': 'sidts-CjIBEJ3XV_fuko41vlUSKjr0XjqiKLQMB-rg7u0XmSt3Qqi1F4P1U5MQz4h8lcs-5n5-LBAA',
# #         'SIDCC': 'AKEyXzUISQMfLqtBZ-Xf6DEQusq45L0k4Q_dtSf7U633xphdLNgvNx8Cbvu_ysRn-YQN5m4sgQGE',
# #         '__Secure-1PSIDCC': 'AKEyXzVUfQsLhn8UiX8vdtFcEbdKnEpLXO-Ol4rhwW45A_cBKWJ1fBgAUfupK9qNembiJjGrDuU',
# #         '__Secure-3PSIDCC': 'AKEyXzUsZ5n4We2DLk8hMAlC0HcKQbK47mOaP8xM5sOzIpu1fg3G4F0bwO-EKPVN73xYJbCB6ow',
# #     }

# #     headers = {
# #         'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
# #         'accept-language': 'en-US,en;q=0.9',
# #         'priority': 'u=0, i',
# #         'referer': 'https://scholar.google.com/citations?hl=en&view_op=search_authors&mauthors=y+lecun&btnG=',
# #         'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
# #         'sec-ch-ua-mobile': '?0',
# #         'sec-ch-ua-platform': '"macOS"',
# #         'sec-fetch-dest': 'document',
# #         'sec-fetch-mode': 'navigate',
# #         'sec-fetch-site': 'same-origin',
# #         'sec-fetch-user': '?1',
# #         'upgrade-insecure-requests': '1',
# #         'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
# #         'x-browser-channel': 'stable',
# #         'x-browser-copyright': 'Copyright 2025 Google LLC. All rights reserved.',
# #         'x-browser-validation': '09P27VycOsIOJE0v6Qg0O++FkSE=',
# #         'x-browser-year': '2025',
# #         'x-client-data': 'CNORywE=',
# #         # 'cookie': 'SID=g.a000ugj-fQTzuxvWidXhAAwQMZcq0mXjrAYe9uoPC-ldxQYUMSWRyDuuX3YbJiZFRqJb9x2l2wACgYKAXISARUSFQHGX2MiqoAozUvlevPy-b21k5XMZxoVAUF8yKo9-qL_kO2PH27rgr310gxj0076; __Secure-1PSID=g.a000ugj-fQTzuxvWidXhAAwQMZcq0mXjrAYe9uoPC-ldxQYUMSWRo7NLBWJnSL6K2aSEXdP30AACgYKAV0SARUSFQHGX2Mi2WMajMCdQwEQFPhz5PPEPxoVAUF8yKqRMphI0aM3c13mAX6Fec_C0076; __Secure-3PSID=g.a000ugj-fQTzuxvWidXhAAwQMZcq0mXjrAYe9uoPC-ldxQYUMSWRl1MhhtJrZ_svTlILE0xMGQACgYKAd0SARUSFQHGX2MioO_qP9PBVTU3bg5JWUEFmRoVAUF8yKrZ4okcOqvHXwE9uuLNjrn70076; HSID=AV6j6nf_VJIj9H0qc; SSID=AXGz_rZeeFAVHZVgz; APISID=5vRTL5l6zaYUWoz6/AtcDLtuyXorP6EeZl; SAPISID=kB_MF2GliJ38pBd_/A2J3geXvHmBshpuij; __Secure-1PAPISID=kB_MF2GliJ38pBd_/A2J3geXvHmBshpuij; __Secure-3PAPISID=kB_MF2GliJ38pBd_/A2J3geXvHmBshpuij; GSP=LM=1741362553:S=CtcxX1EH3-0bWK3p; AEC=AVcja2dvTNm_SyYVTLgByG8nHnSmAIHq5LP8cko9mBIIEkCAnECOryDzMnQ; NID=522=I9-XZucWBQ4eceUYq5-KsaiidEeol2HwFxlYUlrha3-WXU-BreP2LvReCh8-gVI6N75HZJmchizAP4T2S-e5jujfkvCGqlY0_jhjcDMZOxWYwHDc167m9WVStJ6mZLW6w-IdPb6uwIIqq4KMxA3SqS5aX4NPi6F7UDdSrqypgfXrRka-KxFhER73eMJTKr-Jd1xzuDwH62xSsgMjQN7pqEBAeVbwbvpn1b5gFD5ocVDxuiHOxBv2K8FePZV7V5KRlPQ0MvNaWxEsoNMbYU5gbadl3ptlxURe7f-Q4NWeMc8oL75DvnR-eGdB-uzK4Omv1Qfz4c7dnaG9c4w9p4LyrnrVvyjOrZu6KZnpKCDxVV0nENHmzdo2J3WmfOODELtwBBiKOuvVASIKwdJEAiI58fxUgkxWFn3UyaPTNxqbe8RbJABrMjaYvE8qhZVJ6cvap-i0lXJu8i5Ucrp7EYNDyli1Kr87FApOp1qln4ML8_oGFK148Uj52-YxnZizTas59XNCnzPFyCAX-WIckquWaLWQ3JdFlS4LafBBmK7P7Z6ClXhb7TiqyQXfBU20nsccG83elZaajFWBuT2hdeS5C0nwCpEFl_IM4D7r6NFfQiPvWBQiz0I0FSFY347QPkRB-FLo61ekA1ZuDFYVcTHPmzExjJe1RJwG14x0UMobj6DzVM-fv2OzJy6aRiLvuW9V3TqOTEiAkUAgHcDaY3ji8S4b4xNkjAzLJzll9XVskJ3BvF6W5e__aejE5XWZAY3LPg; __Secure-1PSIDTS=sidts-CjIBEJ3XV_fuko41vlUSKjr0XjqiKLQMB-rg7u0XmSt3Qqi1F4P1U5MQz4h8lcs-5n5-LBAA; __Secure-3PSIDTS=sidts-CjIBEJ3XV_fuko41vlUSKjr0XjqiKLQMB-rg7u0XmSt3Qqi1F4P1U5MQz4h8lcs-5n5-LBAA; SIDCC=AKEyXzUISQMfLqtBZ-Xf6DEQusq45L0k4Q_dtSf7U633xphdLNgvNx8Cbvu_ysRn-YQN5m4sgQGE; __Secure-1PSIDCC=AKEyXzVUfQsLhn8UiX8vdtFcEbdKnEpLXO-Ol4rhwW45A_cBKWJ1fBgAUfupK9qNembiJjGrDuU; __Secure-3PSIDCC=AKEyXzUsZ5n4We2DLk8hMAlC0HcKQbK47mOaP8xM5sOzIpu1fg3G4F0bwO-EKPVN73xYJbCB6ow',
# #     }

# #     params = {
# #         'hl': 'en',
# #         'view_op': 'search_authors',
# #         'mauthors': query,
# #         'btnG': '',
# #     }

# #     response = requests.get('https://scholar.google.com/citations', params=params, cookies=cookies, headers=headers)
# #     tree = html.fromstring(response.text)
# #     soup = BeautifulSoup(response.text, "html.parser")
# #     elements = tree.xpath('//*[contains(concat(" ", @class, " "), concat(" ", "gs_ai_chpr", " "))] | //*[contains(concat(" ", @class, " "), concat(" ", "gs_ai_t", " "))]')
# #     results = [html.tostring(elem, encoding="unicode") for elem in elements]
# #     fresults = []
# #     for element in results:
# #         soup = BeautifulSoup(element, "html.parser")
# #         name = soup.find(class_="gs_hlt")
# #         parent = name.find_parent()
# #         url = parent.get("href") if parent.name == "a" else parent.find("a", href=True)
# #         url = url if isinstance(url, str) else url.get("href") if url else None
# #         print(url)
# #         try:
# #             url = "https://scholar.google.com"+url
# #         except:
# #             None
# #         name = parent.get_text()
# #         description = soup.find(class_="gs_ai_aff").get_text()
# #         verified_email = soup.find(class_="gs_ai_eml").get_text().replace("Verified email at ", "")
# #         cite_count = soup.find(class_="gs_ai_cby").get_text().replace("Cited by ", "")
# #         categories = soup.find(class_="gs_ai_int").get_text()
# #         data = {
# #             "name": name,
# #             "description": description,
# #             "verified_email": verified_email,
# #             "cite_count": cite_count,
# #             "categories": categories,
# #             "profile_link": url
# #         }
# #         fresults.append(data)
# #         print(data)
# #     return fresults


@router.get("/")
async def root():
    return {"message": "Twitter API"}

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Twitter API",
        "timestamp": time.time()
    }

@router.get("/profile_info")
async def profile_info(username: str = Query(..., description="account username")):
    cookies = {
        'guest_id_marketing': 'v1%3A174181642626063507',
        'guest_id_ads': 'v1%3A174181642626063507',
        'guest_id': 'v1%3A174181642626063507',
        'kdt': 'fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz',
        'auth_token': '511ff0c295663db421f8a06ba2ff8686e268e693',
        'ct0': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'lang': 'en',
        'twid': 'u%3D897727759358853123',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'personalization_id': '"v1_kEVb+mbPHU0sXvrfEL7zjA=="',
        '__cf_bm': 'EHI6628I5ZF2X2k2pdxfsXTEW18l14boJce9bxVUZhc-1752161917-1.0.1.1-rt.amUMrfa3KqMpIka3xHfoGfCP6cX0CYi8H6XekZKM5_at4I12mJbJAr8lErwl6jOfxXNZLj1Ekw.NGh2fALPgABbff3_M02oEZSXyD85U',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/ChinaDaily',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'iXAttB+CopmrNNMyCPS1vIMsVXPAL9tEsNFa7O+t/bxCkhifQEa1KRwWYofOxYyAE/TyqY2l1KNHoaVJdFv01IoSImfYig',
        'x-csrf-token': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
        'x-xp-forwarded-for': 'f35962fbeda1c959770982bb2cfea226d33cfd1387ec91c5149e2c33bb7b28ce79c03fd351fa318a5860368bb0cfe3f930e37c9e35d55c33d34de8d576839a37b8843a3e1c165d30bf872e28b49aa025c3102ae766167a87bc65a96e4cb794bc5de691684e885db4b7c9da690fe12e62fd1508b4f506aa35e06ae5da455b71f199f5eb0366ced63e34840b93bf57b3e1612c868ee81fb8ca4b3662fea7e85090428bc07167b7e255919a58a39d1a4d205b43c7f94cef5cccc775b2196fd141844885fb21036871998e738cd43f4f834ee5512430da86e65c16fdb29eb5555e226b5b0ec48e092ad31b516abfb851899100ec7031498632d19c00e4f534b864112f',
        # 'cookie': 'guest_id_marketing=v1%3A174181642626063507; guest_id_ads=v1%3A174181642626063507; guest_id=v1%3A174181642626063507; kdt=fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz; auth_token=511ff0c295663db421f8a06ba2ff8686e268e693; ct0=73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958; lang=en; twid=u%3D897727759358853123; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_kEVb+mbPHU0sXvrfEL7zjA=="; __cf_bm=EHI6628I5ZF2X2k2pdxfsXTEW18l14boJce9bxVUZhc-1752161917-1.0.1.1-rt.amUMrfa3KqMpIka3xHfoGfCP6cX0CYi8H6XekZKM5_at4I12mJbJAr8lErwl6jOfxXNZLj1Ekw.NGh2fALPgABbff3_M02oEZSXyD85U',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/ChinaDaily',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'iXAttB+CopmrNNMyCPS1vIMsVXPAL9tEsNFa7O+t/bxCkhifQEa1KRwWYofOxYyAE/TyqY2l1KNHoaVJdFv01IoSImfYig',
        'x-csrf-token': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
        'x-xp-forwarded-for': 'f35962fbeda1c959770982bb2cfea226d33cfd1387ec91c5149e2c33bb7b28ce79c03fd351fa318a5860368bb0cfe3f930e37c9e35d55c33d34de8d576839a37b8843a3e1c165d30bf872e28b49aa025c3102ae766167a87bc65a96e4cb794bc5de691684e885db4b7c9da690fe12e62fd1508b4f506aa35e06ae5da455b71f199f5eb0366ced63e34840b93bf57b3e1612c868ee81fb8ca4b3662fea7e85090428bc07167b7e255919a58a39d1a4d205b43c7f94cef5cccc775b2196fd141844885fb21036871998e738cd43f4f834ee5512430da86e65c16fdb29eb5555e226b5b0ec48e092ad31b516abfb851899100ec7031498632d19c00e4f534b864112f',
        # 'cookie': 'guest_id_marketing=v1%3A174181642626063507; guest_id_ads=v1%3A174181642626063507; guest_id=v1%3A174181642626063507; kdt=fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz; auth_token=511ff0c295663db421f8a06ba2ff8686e268e693; ct0=73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958; lang=en; twid=u%3D897727759358853123; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_kEVb+mbPHU0sXvrfEL7zjA=="; __cf_bm=EHI6628I5ZF2X2k2pdxfsXTEW18l14boJce9bxVUZhc-1752161917-1.0.1.1-rt.amUMrfa3KqMpIka3xHfoGfCP6cX0CYi8H6XekZKM5_at4I12mJbJAr8lErwl6jOfxXNZLj1Ekw.NGh2fALPgABbff3_M02oEZSXyD85U',
    }

    variables = {"screen_name":username}
    params = {
        'variables': json.dumps(variables),
        'features': '{"responsive_web_grok_bio_auto_translation_is_enabled":false,"hidden_profile_subscriptions_enabled":true,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
        'fieldToggles': '{"withAuxiliaryUserLabels":true}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/x3RLKWW1Tl7JgU7YtGxuzw/UserByScreenName',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    # with open('followers_response.json', 'w') as f:
    #     json.dump(response.json(), f)
    # response = requests.get(
    #     'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
    #     params=params,
    #     cookies=cookies,
    #     headers=headers,
    # )
    # print(response.json())
    if not response.json()["data"]:  # Check if "data" is empty
        raise HTTPException(status_code=400, detail="No data available for this profile")

    user_id = response.json()["data"]["user"]["result"]["rest_id"]
    try:
        name = response.json()["data"]["user"]["result"]["core"]["name"]
    except:
        name = ""
    try:
        created_at = response.json()["data"]["user"]["result"]["core"]["created_at"]
    except:
        created_at = ""
    try:
        is_blue_verified = response.json()["data"]["user"]["result"]["is_blue_verified"]
    except:
        is_blue_verified = False
    try:
        verified_since = response.json()["data"]["user"]["result"]["verification_info"]["reason"]["verified_since_msec"]
        verified_since = datetime.fromtimestamp(int(verified_since) / 1000).strftime('%Y-%m-%d %H:%M:%S')
    except:
        verified_since = ""
    try:
        user_name = response.json()["data"]["user"]["result"]["core"]["screen_name"]
    except:
        user_name = ""
    try:
        description = response.json()["data"]["user"]["result"]["legacy"]["description"]
    except:
        description = ""
    try:
        followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
    except:
        followers = 0
    try:
        following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]
    except:
        following = 0
    try:
        avatar_image = response.json()["data"]["user"]["result"]["avatar"]["image_url"]
    except:
        avatar_image = ""
    try:
        profile_image = response.json()["data"]["user"]["result"]["legacy"]["profile_banner_url"]
    except:
        profile_image = ""
    try:
        location = response.json()["data"]["user"]["result"]["location"]["location"]
    except:
        location = ""
    try:
        profile_category = response.json()["data"]["user"]["result"]["professional"]["category"][0]["name"]
    except:
        profile_category = ""
    try:
        professional_type = response.json()["data"]["user"]["result"]["professional"]["professional_type"]
    except:
        professional_type = ""
    try:
        profile_links = response.json()["data"]["user"]["result"]["legacy"]["entities"]["description"][0]["expanded_url"]
    except:
        profile_links = ""
    try:
        profile_urls = response.json()["data"]["user"]["result"]["legacy"]["entities"]["url"]["urls"][0]["expanded_url"]
    except:
        profile_urls = ""
    profile_link = f"https://x.com/{user_name}"
    data = {
        "name": name,
        "user_name": user_name,
        "description": description,
        "created_at": created_at,
        "is_blue_verified": is_blue_verified,
        "verified_since": verified_since,
        "followers_count": followers,
        "following_count": following,
        "avatar_image": avatar_image,
        "profile_image": profile_image,
        "location": location,
        "profile_category": profile_category,
        "professional_type": professional_type,
        "profile_link": profile_link,
        "profile_links": profile_links,
        "profile_urls": profile_urls,
    }
    print(data)
    return data

@router.get("/followers")
async def get_followers(username: str = Query(..., description="account username")):
    followers_list = []
    cookies = {
        'guest_id': '173823245631103789',
        'guest_id_marketing': 'v1%3A173823245631103789',
        'guest_id_ads': 'v1%3A173823245631103789',
        'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
        'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
        'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'twid': 'u%3D1663936852208898049',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'lang': 'en',
        'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
        'priority': 'u=1, i',
        'referer': 'https://x.com/NanouuSymeon',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
        'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
        'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
    }
    variables = {"screen_name":username}

    params = {
        'variables': json.dumps(variables),
        'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
        'fieldToggles': '{"withAuxiliaryUserLabels":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    user_id = response.json()["data"]["user"]["result"]["rest_id"]
    # name = response.json()["data"]["user"]["result"]["legacy"]["name"]
    # description = response.json()["data"]["user"]["result"]["legacy"]["description"]
    # followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
    # following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]

    # print({
    #     "name": name,
    #     "description": description,
    #     "followers_count": followers,
    #     "following_count": following
    # })
    cookies = {
        'guest_id_marketing': 'v1%3A174181642626063507',
        'guest_id_ads': 'v1%3A174181642626063507',
        'guest_id': 'v1%3A174181642626063507',
        'kdt': 'fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz',
        'auth_token': '511ff0c295663db421f8a06ba2ff8686e268e693',
        'ct0': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'lang': 'en',
        'twid': 'u%3D897727759358853123',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'personalization_id': '"v1_kEVb+mbPHU0sXvrfEL7zjA=="',
        '__cf_bm': 'CeQguhO_G9oXrJBRiMPlTSK2W6vYCFQl3Qlz1_3QrzQ-1752162817-1.0.1.1-f.8VV7K58fA7ZYvRevMTKpQyYFCqz_YtSJyiakYBIcIY62BeOi_UT9llDixJG84yfT9uJiF_QZbUFGIZZn_vmPYo63_MvtQv2faNvlcY9u8',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/ChinaDaily/followers',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'S78a/RqjjoMkTjVAtwZdrLEjlOfHPNpWIc/GNt205wmPv10OqcpNa6Ro/QRrEPEUMyHKa08dEABBgrEaW47caassoas4SA',
        'x-csrf-token': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
        'x-xp-forwarded-for': 'aff2de8161d9c391d98ac9ce68e33b94fe83d03d262f3761e2b7e5ab1711b49f18a920520707ce33c1e081a96c306c3affdc6378e723cf88dcb8e52d3982afcb360c4bd3f40f54bb76abd6689b3a5b94149806d1f038b1f987bf0c57e32f848280d83ca1c86e226f7c40e8a7619cda4c2c13863be9242e2bfcdca8ad4f1bf37b8dc4b46ec5e5b71b684bd3ef1dd06c15de44c060ffbb523188551e50137e1c913912a2ba0cca48693f444dfccb75efc3fee51fe64f7f0cca83ccfe6d9bfdf9e3f97e5452966e9ba1eb80e23d88ebb8387311fe6601058ac578ea38c646420e106fb209d5ace7bb15b362a8c11e7b4599ba8803b26fc56398f7eedf9ee079e1d792',
        # 'cookie': 'guest_id_marketing=v1%3A174181642626063507; guest_id_ads=v1%3A174181642626063507; guest_id=v1%3A174181642626063507; kdt=fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz; auth_token=511ff0c295663db421f8a06ba2ff8686e268e693; ct0=73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958; lang=en; twid=u%3D897727759358853123; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_kEVb+mbPHU0sXvrfEL7zjA=="; __cf_bm=CeQguhO_G9oXrJBRiMPlTSK2W6vYCFQl3Qlz1_3QrzQ-1752162817-1.0.1.1-f.8VV7K58fA7ZYvRevMTKpQyYFCqz_YtSJyiakYBIcIY62BeOi_UT9llDixJG84yfT9uJiF_QZbUFGIZZn_vmPYo63_MvtQv2faNvlcY9u8',
    }
    # variables = {
    #     "userId": user_id,
    #     "count": 1000,
    #     "includePromotedContent": True,
    #     "withQuickPromoteEligibilityTweetFields": True,
    #     "withVoice": True,
    #     "withV2Timeline": True
    # }


    # params = {
    #     "variables": json.dumps(variables),
    #     "features": '{"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"articles_preview_enabled":false,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"tweet_with_visibility_results_prefer_gql_media_interstitial_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}',
    # }

    # response = requests.get(
    #     "https://twitter.com/i/api/graphql/ZxuX4tC6kWz9M8pe1i-Gdg/Following",
    #     params=params,
    #     cookies=cookies,
    #     headers=headers,
    # )
    variables = {"userId":user_id,"count":20,"includePromotedContent":False}

    params = {
        'variables': json.dumps(variables),
        'features': '{"rweb_video_screen_enabled":false,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/gjc9BPYkYF-cDv5FdL-29A/Followers',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    # with open('followers_response.json', 'w') as f:
    #     json.dump(response.json(), f)

    # json_data = json.loads(response.text)

    data = response.json()
    # print(data)
    # Extract instructions from the JSON data
    instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    for instruction in instructions:
        if instruction["type"] == "TimelineAddEntries":
            # Extract the entries from the instruction
            entries = instruction["entries"]
            # print(entries)
            # Loop through each entry and extract required information
            for entry in entries:
                # print(entry)
                content = entry["content"]
                try:
                    user_result = content["itemContent"]["user_results"]["result"]
                except:
                    continue
                try:
                    created_at = user_result["core"]["created_at"]
                except:
                    created_at = ""
                try:
                    is_verified = user_result["is_blue_verified"]
                except:
                    is_verified = False
                try:
                    name = user_result["core"]["name"]
                except:
                    name = ""
                try:
                    username = user_result["core"]["screen_name"]
                except:
                    username = ""
                try:
                    followers_count = user_result["legacy"]["followers_count"]
                except:
                    followers_count = 0
                try:
                    friends_count = user_result["legacy"]["friends_count"]
                except:
                    friends_count = 0
                try:
                    description = user_result["legacy"]["description"]
                except:
                    description = ""
                try:
                    profile_avatar = user_result["avatar"]["image_url"]
                except:
                    profile_avatar = ""
                try:
                    profile_banner = user_result["legacy"]["profile_banner_url"]
                except:
                    profile_banner = ""
                # username = user_result["core"]["screen_name"]
                # Print extracted information
                # print(f"Name: {name}")
                # print(f"Followers: {followers_count}")
                # print(f"Following: {friends_count}")
                # print("-------------------------")
                full_data = {
                    "follower_name": name,
                    "created_at": created_at,
                    "is_verified": is_verified,
                    "followers_count": followers_count,
                    "following_count": friends_count,
                    "description": description,
                    "profile_avatar": profile_avatar,
                    "profile_banner": profile_banner,
                    "username": username,
                    "profile_url": f"https://x.com/{username}"
                }
                followers_list.append(full_data)
                # print(full_data)
    cookies = {
        'guest_id_marketing': 'v1%3A174181642626063507',
        'guest_id_ads': 'v1%3A174181642626063507',
        'guest_id': 'v1%3A174181642626063507',
        'kdt': 'fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz',
        'auth_token': '511ff0c295663db421f8a06ba2ff8686e268e693',
        'ct0': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'lang': 'en',
        'twid': 'u%3D897727759358853123',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'personalization_id': '"v1_DH+yNXuinHb5uR8gPTbHuQ=="',
        '__cf_bm': 'YOMsnxYtMvFIJl3xhlNpfefZ_tOC86AFDJGxLva1AZ0-1752169233-1.0.1.1-BkxNuYM5vBN6OVwPPzz9OPf1_hGCMDq5Z9ZGGBbpWbJ3aVDswdjmdNcT8AFs9DXjkNqyiEV0bNRnuiIe.hHfz5Az5trJ3kxO.mnRh2bwpnk',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/ChinaDaily/verified_followers',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-client-transaction-id': '5gwqOHbS1/sIiTpSYzqquGvbASWNXITF2dnpxUOp69y/cnMzAerh3dbBIg2KW37470V/xuLou5orfZWZLywaZ3EPqJoG5Q',
        'x-csrf-token': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
        'x-xp-forwarded-for': '0878cc09af71a82608b1edb76baf2857008b26f4da6d5739f2ecd7f7811e354308376cddab843234404841ae1606cf4aa97c81fe15e590a6cb1e90764d0a0fdee99686ebf681d3f7a6aca2bbad2a0199f18fffc9f745f986ec5898ff61bc07e5fbf1c80785b1ee67eb17d7466ccb0c89922f9daf36e9a8eeb1c6fab90384386677b516322abc3b776cdbb4bfc79a671af85373070315bc58a8fe0a730c3aa3ca0d0ac3e466919bdcf4307d790375b62be54f4a7a31f59aafa2a1b68c0407304356ecfc3f42423a153db93b38577b668ec82894b6e98994e81af2a87ca5a5d0af14adf6591a1f9f00134ca77b66b934f9b1dc0e07f42f60d580c9cb494badd05c',
        # 'cookie': 'guest_id_marketing=v1%3A174181642626063507; guest_id_ads=v1%3A174181642626063507; guest_id=v1%3A174181642626063507; kdt=fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz; auth_token=511ff0c295663db421f8a06ba2ff8686e268e693; ct0=73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958; lang=en; twid=u%3D897727759358853123; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_DH+yNXuinHb5uR8gPTbHuQ=="; __cf_bm=YOMsnxYtMvFIJl3xhlNpfefZ_tOC86AFDJGxLva1AZ0-1752169233-1.0.1.1-BkxNuYM5vBN6OVwPPzz9OPf1_hGCMDq5Z9ZGGBbpWbJ3aVDswdjmdNcT8AFs9DXjkNqyiEV0bNRnuiIe.hHfz5Az5trJ3kxO.mnRh2bwpnk',
    }
    variables = {"userId": user_id,"count":20,"includePromotedContent":False}
    params = {
        'variables': json.dumps(variables),
        'features': '{"rweb_video_screen_enabled":false,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/U_YXAm7JJsfvjFUJwObTdw/BlueVerifiedFollowers',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    # params = {
    #     'variables': json.dumps(variables),
    #     'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    # }

    # response = requests.get(
    #     'https://x.com/i/api/graphql/WijS8Cwfqhtk5hDN9q7sgw/BlueVerifiedFollowers',
    #     params=params,
    #     cookies=cookies,
    #     headers=headers,
    # )
    data = response.json()
    # print(data)
    # Extract instructions from the JSON data
    instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    for instruction in instructions:
        if instruction["type"] == "TimelineAddEntries":
            # Extract the entries from the instruction
            entries = instruction["entries"]
            # Loop through each entry and extract required information
            for entry in entries:
                content = entry["content"]
                try:
                    user_result = content["itemContent"]["user_results"]["result"]
                except:
                    continue
                try:
                    name = user_result["core"]["name"]
                except:
                    name = ""
                try:
                    username = user_result["core"]["screen_name"]
                except:
                    username = ""
                try:
                    followers_count = user_result["legacy"]["followers_count"]
                except:
                    followers_count = 0
                try:
                    friends_count = user_result["legacy"]["friends_count"]
                except:
                    friends_count = 0
                try:
                    description = user_result["legacy"]["description"]
                except:
                    description = ""
                try:
                    profile_avatar = user_result["avatar"]["image_url"]
                except:
                    profile_avatar = ""
                try:
                    profile_banner = user_result["legacy"]["profile_banner_url"]
                except:
                    profile_banner = ""
                try:
                    profile_links = user_result["legacy"]["entities"]["description"]["urls"][0]["expanded_url"]
                except:
                    profile_links = ""
                try:
                    profile_urls = user_result["legacy"]["entities"]["url"]["urls"][0]["expanded_url"]
                except:
                    profile_urls = ""
                try:
                    is_verified = user_result["is_blue_verified"]
                except:
                    is_verified = ""
                # username = user_result["core"]["screen_name"]
                # Print extracted information
                # print(f"Name: {name}")
                # print(f"Followers: {followers_count}")
                # print(f"Following: {friends_count}")
                # print("-------------------------")
                full_data = {
                    "follower_name": name,
                    "followers_count": followers_count,
                    "following_count": friends_count,
                    "description": description,
                    "profile_avatar": profile_avatar,
                    "profile_banner": profile_banner,
                    "profile_links": profile_links,
                    "profile_urls": profile_urls,
                    "username": username,
                    "profile_url": f"https://x.com/{username}",
                    "is_verified": is_verified,
                }
                followers_list.append(full_data)
                # print(full_data)
    cookies = {
        'guest_id_marketing': 'v1%3A174181642626063507',
        'guest_id_ads': 'v1%3A174181642626063507',
        'guest_id': 'v1%3A174181642626063507',
        'kdt': 'fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz',
        'auth_token': '511ff0c295663db421f8a06ba2ff8686e268e693',
        'ct0': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'lang': 'en',
        'twid': 'u%3D897727759358853123',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'personalization_id': '"v1_DH+yNXuinHb5uR8gPTbHuQ=="',
        '__cf_bm': 'YOMsnxYtMvFIJl3xhlNpfefZ_tOC86AFDJGxLva1AZ0-1752169233-1.0.1.1-BkxNuYM5vBN6OVwPPzz9OPf1_hGCMDq5Z9ZGGBbpWbJ3aVDswdjmdNcT8AFs9DXjkNqyiEV0bNRnuiIe.hHfz5Az5trJ3kxO.mnRh2bwpnk',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/ChinaDaily/verified_followers',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-client-transaction-id': '5gwqOHbS1/sIiTpSYzqquGvbASWNXITF2dnpxUOp69y/cnMzAerh3dbBIg2KW37470V/xuLou5orfZWZLywaZ3EPqJoG5Q',
        'x-csrf-token': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
        'x-xp-forwarded-for': '0878cc09af71a82608b1edb76baf2857008b26f4da6d5739f2ecd7f7811e354308376cddab843234404841ae1606cf4aa97c81fe15e590a6cb1e90764d0a0fdee99686ebf681d3f7a6aca2bbad2a0199f18fffc9f745f986ec5898ff61bc07e5fbf1c80785b1ee67eb17d7466ccb0c89922f9daf36e9a8eeb1c6fab90384386677b516322abc3b776cdbb4bfc79a671af85373070315bc58a8fe0a730c3aa3ca0d0ac3e466919bdcf4307d790375b62be54f4a7a31f59aafa2a1b68c0407304356ecfc3f42423a153db93b38577b668ec82894b6e98994e81af2a87ca5a5d0af14adf6591a1f9f00134ca77b66b934f9b1dc0e07f42f60d580c9cb494badd05c',
        # 'cookie': 'guest_id_marketing=v1%3A174181642626063507; guest_id_ads=v1%3A174181642626063507; guest_id=v1%3A174181642626063507; kdt=fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz; auth_token=511ff0c295663db421f8a06ba2ff8686e268e693; ct0=73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958; lang=en; twid=u%3D897727759358853123; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_DH+yNXuinHb5uR8gPTbHuQ=="; __cf_bm=YOMsnxYtMvFIJl3xhlNpfefZ_tOC86AFDJGxLva1AZ0-1752169233-1.0.1.1-BkxNuYM5vBN6OVwPPzz9OPf1_hGCMDq5Z9ZGGBbpWbJ3aVDswdjmdNcT8AFs9DXjkNqyiEV0bNRnuiIe.hHfz5Az5trJ3kxO.mnRh2bwpnk',
    }
    variables = {"userId": user_id,"count":20,"includePromotedContent":False}
    params = {
        'variables': json.dumps(variables),
        'features': '{"rweb_video_screen_enabled":false,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/U_YXAm7JJsfvjFUJwObTdw/BlueVerifiedFollowers',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    # params = {
    #     'variables': json.dumps(variables),
    #     'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    # }

    # response = requests.get(
    #     'https://x.com/i/api/graphql/WijS8Cwfqhtk5hDN9q7sgw/BlueVerifiedFollowers',
    #     params=params,
    #     cookies=cookies,
    #     headers=headers,
    # )
    data = response.json()
    # print(data)
    # Extract instructions from the JSON data
    instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    for instruction in instructions:
        if instruction["type"] == "TimelineAddEntries":
            # Extract the entries from the instruction
            entries = instruction["entries"]
            # Loop through each entry and extract required information
            for entry in entries:
                content = entry["content"]
                try:
                    user_result = content["itemContent"]["user_results"]["result"]
                except:
                    continue
                try:
                    name = user_result["core"]["name"]
                except:
                    name = ""
                try:
                    username = user_result["core"]["screen_name"]
                except:
                    username = ""
                try:
                    followers_count = user_result["legacy"]["followers_count"]
                except:
                    followers_count = 0
                try:
                    friends_count = user_result["legacy"]["friends_count"]
                except:
                    friends_count = 0
                try:
                    description = user_result["legacy"]["description"]
                except:
                    description = ""
                try:
                    profile_avatar = user_result["avatar"]["image_url"]
                except:
                    profile_avatar = ""
                try:
                    profile_banner = user_result["legacy"]["profile_banner_url"]
                except:
                    profile_banner = ""
                try:
                    profile_links = user_result["legacy"]["entities"]["description"]["urls"][0]["expanded_url"]
                except:
                    profile_links = ""
                try:
                    profile_urls = user_result["legacy"]["entities"]["url"]["urls"][0]["expanded_url"]
                except:
                    profile_urls = ""
                try:
                    is_verified = user_result["is_blue_verified"]
                except:
                    is_verified = ""
                # username = user_result["core"]["screen_name"]
                # Print extracted information
                # print(f"Name: {name}")
                # print(f"Followers: {followers_count}")
                # print(f"Following: {friends_count}")
                # print("-------------------------")
                full_data = {
                    "follower_name": name,
                    "followers_count": followers_count,
                    "following_count": friends_count,
                    "description": description,
                    "profile_avatar": profile_avatar,
                    "profile_banner": profile_banner,
                    "profile_links": profile_links,
                    "profile_urls": profile_urls,
                    "username": username,
                    "profile_url": f"https://x.com/{username}",
                    "is_verified": is_verified,
                }
                followers_list.append(full_data)
                # print(full_data)
    cookies = {
        'guest_id_marketing': 'v1%3A174181642626063507',
        'guest_id_ads': 'v1%3A174181642626063507',
        'guest_id': 'v1%3A174181642626063507',
        'kdt': 'fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz',
        'auth_token': '511ff0c295663db421f8a06ba2ff8686e268e693',
        'ct0': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'lang': 'en',
        'twid': 'u%3D897727759358853123',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'personalization_id': '"v1_DH+yNXuinHb5uR8gPTbHuQ=="',
        '__cf_bm': 'YOMsnxYtMvFIJl3xhlNpfefZ_tOC86AFDJGxLva1AZ0-1752169233-1.0.1.1-BkxNuYM5vBN6OVwPPzz9OPf1_hGCMDq5Z9ZGGBbpWbJ3aVDswdjmdNcT8AFs9DXjkNqyiEV0bNRnuiIe.hHfz5Az5trJ3kxO.mnRh2bwpnk',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.5',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/ChinaDaily/verified_followers',
        'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'x-client-transaction-id': '5gwqOHbS1/sIiTpSYzqquGvbASWNXITF2dnpxUOp69y/cnMzAerh3dbBIg2KW37470V/xuLou5orfZWZLywaZ3EPqJoG5Q',
        'x-csrf-token': '73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
        'x-xp-forwarded-for': '0878cc09af71a82608b1edb76baf2857008b26f4da6d5739f2ecd7f7811e354308376cddab843234404841ae1606cf4aa97c81fe15e590a6cb1e90764d0a0fdee99686ebf681d3f7a6aca2bbad2a0199f18fffc9f745f986ec5898ff61bc07e5fbf1c80785b1ee67eb17d7466ccb0c89922f9daf36e9a8eeb1c6fab90384386677b516322abc3b776cdbb4bfc79a671af85373070315bc58a8fe0a730c3aa3ca0d0ac3e466919bdcf4307d790375b62be54f4a7a31f59aafa2a1b68c0407304356ecfc3f42423a153db93b38577b668ec82894b6e98994e81af2a87ca5a5d0af14adf6591a1f9f00134ca77b66b934f9b1dc0e07f42f60d580c9cb494badd05c',
        # 'cookie': 'guest_id_marketing=v1%3A174181642626063507; guest_id_ads=v1%3A174181642626063507; guest_id=v1%3A174181642626063507; kdt=fLqtY4LPPPmjGyt2RisEKIeUwmbdQpDRQSESlxSz; auth_token=511ff0c295663db421f8a06ba2ff8686e268e693; ct0=73d0b6a6fc55883ba079cefc94d9d1c3cd1b842fbad73699731a9ac9bad9156acaee8131a38ca1c59ea3c37632178631e79fce54e18e0802ff9de7dbf7627349b7ccb193784d2e8a61416eb185165958; lang=en; twid=u%3D897727759358853123; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_DH+yNXuinHb5uR8gPTbHuQ=="; __cf_bm=YOMsnxYtMvFIJl3xhlNpfefZ_tOC86AFDJGxLva1AZ0-1752169233-1.0.1.1-BkxNuYM5vBN6OVwPPzz9OPf1_hGCMDq5Z9ZGGBbpWbJ3aVDswdjmdNcT8AFs9DXjkNqyiEV0bNRnuiIe.hHfz5Az5trJ3kxO.mnRh2bwpnk',
    }
    variables = {"userId": user_id,"count":20,"includePromotedContent":False}
    params = {
        'variables': json.dumps(variables),
        'features': '{"rweb_video_screen_enabled":false,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/U_YXAm7JJsfvjFUJwObTdw/BlueVerifiedFollowers',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    # params = {
    #     'variables': json.dumps(variables),
    #     'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    # }

    # response = requests.get(
    #     'https://x.com/i/api/graphql/WijS8Cwfqhtk5hDN9q7sgw/BlueVerifiedFollowers',
    #     params=params,
    #     cookies=cookies,
    #     headers=headers,
    # )
    data = response.json()
    # print(data)
    # Extract instructions from the JSON data
    instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    for instruction in instructions:
        if instruction["type"] == "TimelineAddEntries":
            # Extract the entries from the instruction
            entries = instruction["entries"]
            # Loop through each entry and extract required information
            for entry in entries:
                content = entry["content"]
                try:
                    user_result = content["itemContent"]["user_results"]["result"]
                except:
                    continue
                try:
                    name = user_result["core"]["name"]
                except:
                    name = ""
                try:
                    username = user_result["core"]["screen_name"]
                except:
                    username = ""
                try:
                    followers_count = user_result["legacy"]["followers_count"]
                except:
                    followers_count = 0
                try:
                    friends_count = user_result["legacy"]["friends_count"]
                except:
                    friends_count = 0
                try:
                    description = user_result["legacy"]["description"]
                except:
                    description = ""
                try:
                    profile_avatar = user_result["avatar"]["image_url"]
                except:
                    profile_avatar = ""
                try:
                    profile_banner = user_result["legacy"]["profile_banner_url"]
                except:
                    profile_banner = ""
                try:
                    profile_links = user_result["legacy"]["entities"]["description"]["urls"][0]["expanded_url"]
                except:
                    profile_links = ""
                try:
                    profile_urls = user_result["legacy"]["entities"]["url"]["urls"][0]["expanded_url"]
                except:
                    profile_urls = ""
                try:
                    is_verified = user_result["is_blue_verified"]
                except:
                    is_verified = ""
                # username = user_result["core"]["screen_name"]
                # Print extracted information
                # print(f"Name: {name}")
                # print(f"Followers: {followers_count}")
                # print(f"Following: {friends_count}")
                full_data = {
                    "follower_name": name,
                    "followers_count": followers_count,
                    "following_count": friends_count,
                    "description": description,
                    "profile_avatar": profile_avatar,
                    "profile_banner": profile_banner,
                    "profile_links": profile_links,
                    "profile_urls": profile_urls,
                    "username": username,
                    "profile_url": f"https://x.com/{username}",
                    "is_verified": is_verified,
                }
                followers_list.append(full_data)
                # print(full_data)
    print(followers_list)
    print(len(followers_list))
    return followers_list


@router.get("/following")
async def get_following(username: str = Query(..., description="account username")):
    following_list = []
    cookies = {
        'guest_id': '173823245631103789',
        'guest_id_marketing': 'v1%3A173823245631103789',
        'guest_id_ads': 'v1%3A173823245631103789',
        'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
        'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
        'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'twid': 'u%3D1663936852208898049',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'lang': 'en',
        'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
        'priority': 'u=1, i',
        'referer': 'https://x.com/NanouuSymeon',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
        'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
        'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
    }
    variables = {"screen_name":username}

    params = {
        'variables': json.dumps(variables),
        'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
        'fieldToggles': '{"withAuxiliaryUserLabels":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    user_id = response.json()["data"]["user"]["result"]["rest_id"]
    # name = response.json()["data"]["user"]["result"]["legacy"]["name"]
    # description = response.json()["data"]["user"]["result"]["legacy"]["description"]
    # followers = response.json()["data"]["user"]["result"]["legacy"]["followers_count"]
    # following = response.json()["data"]["user"]["result"]["legacy"]["friends_count"]

    # print({
    #     "name": name,
    #     "description": description,
    #     "followers_count": followers,
    #     "following_count": following
    # })

    cookies = {
        'guest_id': '173823245631103789',
        'guest_id_marketing': 'v1%3A173823245631103789',
        'guest_id_ads': 'v1%3A173823245631103789',
        'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
        'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
        'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'twid': 'u%3D1663936852208898049',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'lang': 'en',
        'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        # 'cookie': 'guest_id=173823245631103789; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
        'priority': 'u=1, i',
        'referer': 'https://x.com/NanouuSymeon/following',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'K6T2901oKUgwBSYdUdPB/cKTP7f83oLUAJRJR3gsdYqeLMYjv41eWfHJ+bkdkSEVZANZXCjryv+TtCozg0cw7MLZidmRKA',
        'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
        'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
    }

    variables = {"userId":user_id,"count":1000,"includePromotedContent":False}

    params = {
        'variables': json.dumps(variables),
        'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/o5eNLkJb03ayTQa97Cpp7w/Following',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    data = json.loads(response.text)
    # print(data)
    # Extract instructions from the JSON data
    instructions = data["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    for instruction in instructions:
        if instruction["type"] == "TimelineAddEntries":
            # Extract the entries from the instruction
            entries = instruction["entries"]
            # Loop through each entry and extract required information
            for entry in entries:
                content = entry["content"]
                try:
                    user_result = content["itemContent"]["user_results"]["result"]
                except:
                    continue
                try:
                    name = user_result["legacy"]["name"]
                except:
                    name = ""
                try:
                    followers_count = user_result["legacy"]["followers_count"]
                except:
                    followers_count = 0
                try:
                    profile_links = user_result["legacy"]["entities"]["description"]["urls"][0]["expanded_url"]
                except:
                    profile_links = ""
                try:
                    profile_urls = user_result["legacy"]["entities"]["url"]["urls"][0]["expanded_url"]
                except:
                    profile_urls = ""
                try:
                    banner_url = user_result["legacy"]["profile_banner_url"]
                except:
                    banner_url = ""
                try:
                    profile_avatar = user_result["legacy"]["profile_image_url_https"]
                except:
                    profile_avatar = ""
                try:
                    friends_count = user_result["legacy"]["friends_count"]
                except:
                    friends_count = 0
                try:
                    is_verified = user_result["is_blue_verified"]
                except:
                    is_verified = ""
                try:
                    description = user_result["legacy"]["description"]
                except:
                    description = ""
                try:
                    username = user_result["legacy"]["screen_name"]
                except:
                    username = ""
                full_data = {
                    "follower_name": name,
                    "followers_count": followers_count,
                    "following_count": friends_count,
                    "description": description,
                    "username": username,
                    "profile_url": f"https://x.com/{username}",
                    "profile_links": profile_links,
                    "profile_urls": profile_urls,
                    "profile_avatar": profile_avatar,
                    "profile_banner": banner_url,
                    "is_verified": is_verified
                }
                following_list.append(full_data)
                # print(full_data)
    print(following_list)
    print(len(following_list))
    return following_list


@router.get("/posts")
async def get_profile_posts(
    username: str = Query(..., description="account username"),
    cursor: str = Query(None, description="pagination cursor (from previous response)")
):
    posts_list = []
    cookies = {
        'guest_id': '173823245631103789',
        'guest_id_marketing': 'v1%3A173823245631103789',
        'guest_id_ads': 'v1%3A173823245631103789',
        'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
        'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
        'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'twid': 'u%3D1663936852208898049',
        'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
        'lang': 'en',
        'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
    }

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        'content-type': 'application/json',
        'priority': 'u=1, i',
        'referer': 'https://x.com/NanouuSymeon',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'x-client-transaction-id': 'hglbWuDFhOWdqIuw/H5sUG8+khpRcy95rTnk6tWB2CczgWuOEiDz9FxkVBSwPIy4yfZW8IWqiYX7bJYP2oZnHaHR4t1PhQ',
        'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
        'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
        'x-twitter-active-user': 'yes',
        'x-twitter-auth-type': 'OAuth2Session',
        'x-twitter-client-language': 'en',
    }
    variables = {"screen_name":username}

    params = {
        'variables': json.dumps(variables),
        'features': '{"hidden_profile_subscriptions_enabled":true,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}',
        'fieldToggles': '{"withAuxiliaryUserLabels":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/32pL5BWe9WKeSK1MoPvFQQ/UserByScreenName',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    user_id = response.json()["data"]["user"]["result"]["rest_id"]

    # Initialize variables for the posts request
    variables = {
        "userId": user_id,
        "count": 20,
        "includePromotedContent": True,
        "withQuickPromoteEligibilityTweetFields": True,
        "withVoice": True,
        "withV2Timeline": True
    }

    # Add cursor if provided
    if cursor:
        variables["cursor"] = cursor
        print(f"Using provided cursor: {cursor}")

    print(f"Variables for UserTweets request: {json.dumps(variables, indent=2)}")

    params = {
        'variables': json.dumps(variables),
        'features': '{"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":false,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":false,"responsive_web_enhance_cards_enabled":false}',
        'fieldToggles': '{"withArticlePlainText":false}',
    }

    response = requests.get(
        'https://x.com/i/api/graphql/Y9WM4Id6UcGFE8Z-hbnixw/UserTweets',
        params=params,
        cookies=cookies,
        headers=headers,
    )

    print(f"Twitter API status: {response.status_code}")
    print(f"Twitter API response (first 500 chars): {response.text[:500]}")

    # Check for API errors
    if response.status_code != 200:
        print(f"Twitter API error: {response.status_code}")
        print(f"Response: {response.text}")
        raise HTTPException(status_code=500, detail=f"Twitter API error: {response.status_code}")

    posts = response.json()
    
    # Check if the response has errors
    if "errors" in posts:
        print(f"Twitter API returned errors: {posts['errors']}")
        raise HTTPException(status_code=500, detail="Twitter API returned errors")
    
    # Robustly find the entries by looking for TimelineAddEntries instruction
    entries = None
    instructions = posts["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
    
    for instruction in instructions:
        if instruction.get("type") == "TimelineAddEntries":
            entries = instruction.get("entries", [])
            break
    
    if entries is None:
        # Fallback: try to find any instruction with entries
        for instruction in instructions:
            if "entries" in instruction:
                entries = instruction["entries"]
                break
    
    if entries is None:
        print("No entries found in Twitter API response")
        entries = []
    
    print(f"Found {len(entries)} entries")

    # Extract cursor for next page (Bottom cursor)
    next_cursor = None
    for entry in entries:
        if entry.get("content", {}).get("entryType") == "TimelineTimelineCursor":
            cursor_type = entry["content"].get("cursorType")
            if cursor_type == "Bottom":
                next_cursor = entry["content"]["value"]
                break
    if next_cursor:
        print(f"Next cursor to return: {next_cursor}")

    # Filter out cursor entries from posts processing
    actual_posts = [entry for entry in entries if entry.get("content", {}).get("entryType") != "TimelineTimelineCursor"]

    for entries in actual_posts:
            post_url = f'https://x.com/{username}/status/{(entries["entryId"].split("-"))[1]}'
            try:
                entriess = entries["content"]["items"]
            except:
                entriess = []
            if len(entriess) == 0:
                try:
                    views = entries["content"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
                except:
                    views = None
                try:
                    bookmarks = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
                except:
                    bookmarks = None
                try:
                    tweet_date = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
                except:
                    tweet_date = None
                if tweet_date is None:
                    continue
                try:
                    media_type = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
                except:
                    media_type = None
                try:
                    likes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
                except:
                    likes =None
                try:
                    tweet_text = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
                    if "RT @" in tweet_text:
                        isretweet = True
                    else:
                        isretweet = False
                except:
                    tweet_text = None
                try:
                    quotes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
                except:
                    quotes = None
                try:
                    replies = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
                except:
                    replies = None
                try:
                    retweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
                except:
                    retweet =  None
                try:
                    quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
                except:
                    quoted_tweet = None
                try:
                    url = post_url
                except:
                    url = None

                data = {
                    "views": views,
                    "bookmarks": bookmarks,
                    "tweet_date": tweet_date,
                    "media_type": media_type,
                    "likes": likes,
                    "tweet_text": tweet_text,
                    "quotes": quotes,
                    "replies": replies,
                    "retweetc": retweet,
                    "thread_tweet": False,
                    "quoted_tweet": quoted_tweet,
                    "isRetweet": isretweet,
                    "url": url
                }
                posts_list.append(data)
            else:
                for entry in entriess:
                    try:
                        views = entry["item"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
                    except:
                        views = None
                    try:
                        bookmarks = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
                    except:
                        bookmarks = None
                    try:
                        tweet_date = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
                    except:
                        tweet_date = None
                    if tweet_date is None:
                        continue
                    try:
                        media_type = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
                    except:
                        media_type = None
                    try:
                        likes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
                    except:
                        likes =None
                    try:
                        tweet_text = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
                        if "RT @" in tweet_text:
                            isretweet = True
                        else:
                            isretweet = False
                    except:
                        tweet_text = None
                    try:
                        quotes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
                    except:
                        quotes = None
                    try:
                        replies = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
                    except:
                        replies = None
                    try:
                        retweet = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
                    except:
                        retweet =  None
                    try:
                        quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
                    except:
                        quoted_tweet = None
                    try:
                        url = post_url
                    except:
                        url = None

                    data = {
                        "views": views,
                        "bookmarks": bookmarks,
                        "tweet_date": tweet_date,
                        "media_type": media_type,
                        "likes": likes,
                        "tweet_text": tweet_text,
                        "quotes": quotes,
                        "replies": replies,
                        "retweetc": retweet,
                        "quoted_tweet": quoted_tweet,
                        "thread_tweet": True,
                        "isRetweet": isretweet,
                        "url": url
                    }
                    posts_list.append(data)

    return {
        "posts": posts_list,
        "next_cursor": next_cursor,
        "has_more": next_cursor is not None,
        "total_posts_in_page": len(posts_list)
    }


# @router.get("/search")
# async def search_tweets(
#     query: str = Query(..., description="search query"),
#     result_type: str = Query("Top", description="Search result type: 'Top' (popular) or 'Latest' (recent)"),
#     cursor: str = Query(None, description="pagination cursor (from previous response)")
# ):
#     cookies = {
#         'guest_id': 'v1%3A171353782335253191',
#         'twid': 'u%3D1663936852208898049',
#         'auth_token': 'b27ab02b6fbcf00d1db8e7bf1a319d973084924b',
#         'guest_id_ads': 'v1%3A171353782335253191',
#         'guest_id_marketing': 'v1%3A171353782335253191',
#         'ct0': '52d09056b351acee0d101bbf7949c3f45be213602e00f6241942e4b963a61e471032b0d0db10318ac97d8b6c5c302bb4936c21d8dd39f3ef0ed3d1e3467c2fd79b1e34ee44fdbcd8510bf5a82f158376',
#         'lang': 'en',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'personalization_id': '"v1_WUjf0NUgaPWRX4efQJqAqA=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.5',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com',
#         'sec-ch-ua': '"Brave";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'g7kus5wNnyIeKG8Dn68Bv5stgeTu4k4VYskkPw21zMuc1oE59rpwZrX4YtAHV3HIL5sZroC7n1uryGd3nqsgM0/KLnK7gA',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '52d09056b351acee0d101bbf7949c3f45be213602e00f6241942e4b963a61e471032b0d0db10318ac97d8b6c5c302bb4936c21d8dd39f3ef0ed3d1e3467c2fd79b1e34ee44fdbcd8510bf5a82f158376',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }

#     # Validate result_type parameter
#     if result_type not in ["Top", "Latest"]:
#         raise HTTPException(status_code=400, detail="result_type must be either 'Top' or 'Latest'")

#     url = f'https://x.com/i/api/graphql/BkkaU7QQGQBGnYgk4pKh4g/SearchTimeline'
#     variables = {
#         "rawQuery": query,
#         "count": 100,
#         "querySource": "typed_query",
#         "product": result_type
#     }
    
#     # Add cursor if provided
#     if cursor:
#         variables["cursor"] = cursor
#         print(f"Using provided cursor: {cursor}")
#     features = {
#         "responsive_web_grok_share_attachment_enabled": False,
#         "freedom_of_speech_not_reach_fetch_enabled": True,
#         "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
#         "responsive_web_twitter_article_tweet_consumption_enabled": True,
#         "rweb_tipjar_consumption_enabled": True,
#         "profile_label_improvements_pcf_label_in_post_enabled": False,
#         "longform_notetweets_rich_text_read_enabled": True,
#         "standardized_nudges_misinfo": True,
#         "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
#         "responsive_web_grok_analyze_post_followups_enabled": True,
#         "premium_content_api_read_enabled": False,
#         "rweb_video_timestamps_enabled": True,
#         "responsive_web_enhance_cards_enabled": False,
#         "longform_notetweets_inline_media_enabled": True,
#         "communities_web_enable_tweet_community_results_fetch": True,
#         "verified_phone_label_enabled": False,
#         "creator_subscriptions_tweet_preview_api_enabled": True,
#         "c9s_tweet_anatomy_moderator_badge_enabled": True,
#         "responsive_web_edit_tweet_api_enabled": True,
#         "view_counts_everywhere_api_enabled": True,
#         "tweet_awards_web_tipping_enabled": False,
#         "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
#         "articles_preview_enabled": True,
#         "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
#         "creator_subscriptions_quote_tweet_preview_enabled": False,
#         "longform_notetweets_consumption_enabled": True,
#         "responsive_web_graphql_exclude_directive_enabled": True,
#         "responsive_web_graphql_timeline_navigation_enabled": True,
#     }
#     params = {
#         'variables': json.dumps(variables),
#         'features': json.dumps(features),
#     }

#     response = requests.get(url, cookies=cookies, headers=headers, params=params)
#     try:
#         data = response.json()
#     except:
#         raise HTTPException(status_code=500, detail="Could not extract posts from Twitter API response")
#     # print(f"THIS IS THE DATA: {data}")

#     # if result_type == "Latest":
#     #     try:
#     #         posts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][0]["entries"]
#     #     except:
#     #         posts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][1]["entries"]
#     # elif result_type == "Top":
#     #     try:
#     #         posts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][1]["entries"]
#     #     except:
#     #         posts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][0]["entries"]
#     posts = next(
#                 (entry["entries"] for entry in data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"] 
#                 if entry["type"] == "TimelineAddEntries"), 
#                 []
#             )

#     # Extract cursor for next page (Bottom cursor)
#     next_cursor = None
#     for entry in posts:
#         if entry.get("content", {}).get("entryType") == "TimelineTimelineCursor":
#             cursor_type = entry["content"].get("cursorType")
#             if cursor_type == "Bottom":
#                 next_cursor = entry["content"]["value"]
#                 break
#     if next_cursor:
#         print(f"Next cursor to return: {next_cursor}")

#     # Filter out cursor entries from posts processing
#     actual_posts = [entry for entry in posts if entry.get("content", {}).get("entryType") != "TimelineTimelineCursor"]

#     posts_list = []

#     for entries in actual_posts:
#         if "tweet-" not in entries["entryId"]:
#             continue
        
#         # Check if this entry actually has tweet data
#         try:
#             content = entries.get("content", {})
#             item_content = content.get("itemContent", {})
#             if "tweet_results" not in item_content:
#                 continue
#         except:
#             continue
            
#         # post_url = entries["entryId"]
#         try:
#             entriess = entries["content"]["items"]
#             # print(len(entriess))
#         except:
#             entriess = []
#             # print(f"len of entriesss {len(entriess)}")
#             # print(len(entriess)==0)
#         if len(entriess) == 0:
#             # Try multiple possible structures for username
#             username = None
#             try:
#                 # New structure: core -> user_results -> result -> legacy -> screen_name
#                 username = entries["content"]["itemContent"]["tweet_results"]["result"]["core"]["user_results"]["result"]["legacy"]["screen_name"]
#             except:
#                 try:
#                     # Old structure: direct legacy -> screen_name
#                     username = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["screen_name"]
#                 except:
#                     try:
#                         # Alternative structure: legacy -> user -> screen_name
#                         username = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["user"]["screen_name"]
#                     except:
#                         # If all fail, try to extract from user_id_str or other fields
#                         try:
#                             user_id = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["user_id_str"]
#                             username = f"user_{user_id}"
#                         except:
#                             username = "unknown_user"
#             post_url = f'https://x.com/{username}/status/{(entries["entryId"].split("-"))[1]}'
#             try:
#                 views = entries["content"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
#             except:
#                 views = None
#             try:
#                 bookmarks = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
#             except:
#                 bookmarks = None
#             try:
#                 tweet_date = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
#             except:
#                 tweet_date = None
#             if tweet_date is None:
#                 continue
#             try:
#                 media_type = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
#             except:
#                 media_type = None
#             try:
#                 likes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
#             except:
#                 likes =None
#             try:
#                 tweet_text = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
#                 if "RT @" in tweet_text:
#                     isretweet = True
#                 else:
#                     isretweet = False
#             except:
#                 tweet_text = None
#             try:
#                 quotes = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
#             except:
#                 quotes = None
#             try:
#                 replies = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
#             except:
#                 replies = None
#             try:
#                 retweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
#             except:
#                 retweet =  None
#             try:
#                 quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
#             except:
#                 quoted_tweet = None
#             try:
#                 url = post_url
#             except:
#                 url = None

#             data = {
#                 "views": views,
#                 "bookmarks": bookmarks,
#                 "tweet_date": tweet_date,
#                 "media_type": media_type,
#                 "likes": likes,
#                 "tweet_text": tweet_text,
#                 "quotes": quotes,
#                 "replies": replies,
#                 "retweetc": retweet,
#                 "thread_tweet": False,
#                 "quoted_tweet": quoted_tweet,
#                 "isRetweet": isretweet,
#                 "url": url
#             }
#             posts_list.append(data)
#             print(data)

#         else:
#             for entry in entriess:
#                 username = entry["item"]["itemContent"]["tweet_results"]["result"]["core"]["user_results"]["result"]["legacy"]["screen_name"]
#                 post_url = f'https://x.com/{username}/status/{(entries["entryId"].split("-"))[1]}'
#                 try:
#                     views = entry["item"]["itemContent"]["tweet_results"]["result"]["views"]["count"]
#                 except:
#                     views = None
#                 try:
#                     bookmarks = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["bookmark_count"]
#                 except:
#                     bookmarks = None
#                 try:
#                     tweet_date = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["created_at"]
#                 except:
#                     tweet_date = None
#                 if tweet_date is None:
#                     continue
#                 try:
#                     media_type = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["entities"]["media"][0]["type"]
#                 except:
#                     media_type = None
#                 try:
#                     likes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["favorite_count"]
#                 except:
#                     likes =None
#                 try:
#                     tweet_text = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["full_text"]
#                     if "RT @" in tweet_text:
#                         isretweet = True
#                     else:
#                         isretweet = False
#                 except:
#                     tweet_text = None
#                 try:
#                     quotes = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["quote_count"]
#                 except:
#                     quotes = None
#                 try:
#                     replies = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["reply_count"]
#                 except:
#                     replies = None
#                 try:
#                     retweet = entry["item"]["itemContent"]["tweet_results"]["result"]["legacy"]["retweet_count"]
#                 except:
#                     retweet =  None
#                 try:
#                     quoted_tweet = entries["content"]["itemContent"]["tweet_results"]["result"]["legacy"]["quoted_status_permalink"]["url"]
#                 except:
#                     quoted_tweet = None
#                 try:
#                     url = post_url
#                 except:
#                     url = None
                
#                 data = {
#                     "views": views,
#                     "bookmarks": bookmarks,
#                     "tweet_date": tweet_date,
#                     "media_type": media_type,
#                     "likes": likes,
#                     "tweet_text": tweet_text,
#                     "quotes": quotes,
#                     "replies": replies,
#                     "retweetc": retweet,
#                     "quoted_tweet": quoted_tweet,
#                     "thread_tweet": True,
#                     "isRetweet": isretweet,
#                     "url": url
#                 }
#                 posts_list.append(data)
#                 print(data)
    
#     return {
#         "posts": posts_list,
#         "next_cursor": next_cursor,
#         "has_more": next_cursor is not None,
#         "total_results": len(posts_list)
#     }


def get_next_page_url_from_soup(soup: BeautifulSoup):
    """
    Get the next page URL from the 'Load more' link on a Nitter search page.
    
    This mimics the Playwright helper:
      - Find all '.show-more a' links
      - Pick the one with text 'Load more'
      - Normalize relative hrefs to full https://nitter.net URLs
    """
    all_show_more_links = soup.select(".show-more a")

    for link in all_show_more_links:
        if link.get_text(strip=True) == "Load more":
            href = link.get("href")
            if not href:
                return None

            # If href starts with '/', it's an absolute path, use it as is
            # If href starts with '?', append it to the base search URL
            if href.startswith("/"):
                return f"https://nitter.net{href}"
            elif href.startswith("?"):
                return f"https://nitter.net/search{href}"

            return href

    return None


# Proxy rotation for Nitter (generated on the fly using the same pattern as proxies_new.txt)
PROXY_HOST = "p.webshare.io"
PROXY_PORT = 80
PROXY_USER_PREFIX = "vuidbdcu-"
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
print("PROXY_PASSWORD", PROXY_PASSWORD)
PROXY_COUNT = 1000  # vuidbdcu-1 ... vuidbdcu-1000
_nitter_proxy_index = 0


def get_next_nitter_proxy() -> Dict[str, str]:
    """
    Get the next proxy in sequence for Nitter requests.
    
    Proxies are generated on the fly using the pattern:
      p.webshare.io:80:vuidbdcu-{n}:lt12nel60x4y
    
    Each call advances the index; when we reach PROXY_COUNT we wrap to 1 again.
    """
    global _nitter_proxy_index

    proxy_num = (_nitter_proxy_index % PROXY_COUNT) + 1
    _nitter_proxy_index += 1

    username = f"{PROXY_USER_PREFIX}{proxy_num}"
    url = f"http://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"

    return {
        "http": url,
        "https": url,
    }


@router.get("/search")
async def search_tweets(
    query: str = Query(..., description="Search tweets query (via Nitter HTML)"),
    cursor: str = Query(None, description="Pagination cursor (from previous response)"),
):
    """
    Search for tweets on X (Twitter) using Nitter HTML, one page at a time.
    
    - Each request returns only the results on the current page.
    - If there is another page, a `next_cursor` is returned.
    - The client can pass that `next_cursor` back in the next request to get the next page.
    """
    logger.info(f"🌐 /twitter/search (Nitter) - query='{query}', cursor='{cursor}'")

    base_params = {
        "f": "tweets",
        "q": query,
    }

    # Build params for this page
    params = dict(base_params)
    if cursor:
        params["cursor"] = cursor

    logger.info(f"🔎 Nitter tweet search - fetching page with params={params}")

    # Use a rotated proxy for this Nitter request
    proxies = get_next_nitter_proxy()
    logger.info(f"🌐 Using Nitter proxy (tweets): {proxies['http']}")

    try:
        response = curl_requests.get(
            "https://nitter.net/search",
            params=params,
            impersonate="chrome",
            proxies=proxies,
        )
    except Exception as e:
        logger.error(f"❌ Error calling Nitter for tweets: {e}")
        raise HTTPException(status_code=502, detail="Error contacting Nitter for tweet search")

    html = response.text

    # Log a snippet of the raw HTML so we can see what Nitter returns in deployment
    logger.info(
        "🌐 Nitter raw HTML (tweets) length=%s, snippet=%r",
        len(html),
        html[:500],
        "resonse status code", response.status_code
    )

    # Optional: keep last page HTML for debugging if needed on disk
    with open("nitter.html", "w", encoding="utf-8") as f:
        f.write(html)

    soup = BeautifulSoup(html, "html.parser")

    tweets: List[Dict[str, Any]] = []
    page_tweet_count = 0

    for item in soup.select("div.timeline-item[data-username]"):
        username_slug = item.get("data-username")

        # Tweet link and IDs
        tweet_link_tag = item.select_one("a.tweet-link")
        tweet_path = tweet_link_tag.get("href") if tweet_link_tag else None  # e.g. "/user/status/123#m"
        tweet_url = None
        tweet_id = None
        if tweet_path:
            # Strip off any "#m" fragment
            path_no_fragment = tweet_path.split("#", 1)[0]
            tweet_url = f"https://x.com{path_no_fragment}"
            # Extract tweet ID from "/{user}/status/{id}"
            parts = path_no_fragment.split("/")
            if "status" in parts:
                try:
                    tweet_id = parts[parts.index("status") + 1]
                except (ValueError, IndexError):
                    tweet_id = None

        header = item.select_one("div.tweet-header")
        if not header:
                continue

        # Handle / X screen name
        profile_link_tag = header.select_one("a.username")
        handle_text = profile_link_tag.get_text(strip=True) if profile_link_tag else None  # e.g. "@user"
        if handle_text and handle_text.startswith("@"):
            screen_name = handle_text[1:]
        else:
            screen_name = username_slug

        # X profile URL
        profile_url = f"https://x.com/{screen_name}" if screen_name else None

        # Display name (prefer title attribute to avoid inline icons)
        fullname_tag = header.select_one("a.fullname")
        if fullname_tag and fullname_tag.get("title"):
            display_name = fullname_tag.get("title")
        else:
            display_name = fullname_tag.get_text(strip=True) if fullname_tag else None

        # Verified badge
        verified = bool(header.select_one(".verified-icon"))

        # Timestamp
        date_link = header.select_one("span.tweet-date a")
        created_at = date_link.get("title") if date_link and date_link.get("title") else None
        time_ago = date_link.get_text(strip=True) if date_link else None

        # Retweet info
        retweet_header = item.select_one("div.retweet-header")
        retweeted_by = None
        if retweet_header:
            # Example text: "Some User retweeted"
            retweet_text = retweet_header.get_text(" ", strip=True)
            if "retweeted" in retweet_text:
                retweeted_by = retweet_text.replace("retweeted", "").strip()

        # Replying-to info – return X profile URLs instead of raw @handles
        replying_to_tag = item.select_one("div.replying-to")
        replying_to = None
        if replying_to_tag:
            urls: List[str] = []
            for a in replying_to_tag.select("a"):
                href = a.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    urls.append(f"https://x.com{href}")
                else:
                    urls.append(href)
            replying_to = urls or None

        # Main tweet text
        content_tag = item.select_one("div.tweet-content.media-body")
        text = content_tag.get_text(" ", strip=True) if content_tag else None

        # Quoted tweet (if any)
        quote_block = item.select_one("div.quote")
        quoted_tweet_url = None
        quoted_username = None
        quoted_display_name = None
        quoted_text = None
        if quote_block:
            quote_link = quote_block.select_one("a.quote-link")
            quote_path = quote_link.get("href") if quote_link else None
            if quote_path:
                quoted_tweet_url = f"https://x.com{quote_path.split('#', 1)[0]}"

            quote_header = quote_block.select_one("div.tweet-name-row")
            if quote_header:
                q_fullname = quote_header.select_one("a.fullname")
                q_username = quote_header.select_one("a.username")
                quoted_display_name = q_fullname.get("title") if q_fullname and q_fullname.get("title") else (
                    q_fullname.get_text(strip=True) if q_fullname else None
                )
                if q_username:
                    q_handle = q_username.get_text(strip=True)
                    quoted_username = q_handle[1:] if q_handle.startswith("@") else q_handle

            quote_text_tag = quote_block.select_one("div.quote-text")
            quoted_text = quote_text_tag.get_text(" ", strip=True) if quote_text_tag else None

        # Stats: replies, retweets, likes, views
        stats_block = item.select_one("div.tweet-stats")
        reply_count = retweet_count = like_count = view_count = None
        if stats_block:
            stat_spans = stats_block.select("span.tweet-stat")

            def parse_count(span):
                if not span:
                    return None
                txt = span.get_text(" ", strip=True).replace(",", "")
                parts = [p for p in txt.split(" ") if p.replace(",", "").isdigit()]
                if not parts:
                    return None
                try:
                    return int(parts[-1])
                except ValueError:
                    return None

            if len(stat_spans) > 0:
                reply_count = parse_count(stat_spans[0])
            if len(stat_spans) > 1:
                retweet_count = parse_count(stat_spans[1])
            if len(stat_spans) > 2:
                like_count = parse_count(stat_spans[2])
            if len(stat_spans) > 3:
                view_count = parse_count(stat_spans[3])

        # Media URLs in X format:
        #   https://x.com/{screen_name}/status/{tweet_id}/photo/{index}
        #   https://x.com/{quoted_username}/status/{quoted_tweet_id}/photo/{index}
        media_urls = []
        quoted_media_urls = []

        main_media_index = 1
        quoted_media_index = 1
        for img in item.select("div.attachments img"):
            inside_quote = img.find_parent("div", class_="quote") is not None

            if inside_quote and quoted_tweet_url and quoted_username:
                quoted_tweet_id = None
                try:
                    q_path = quoted_tweet_url.split("https://x.com", 1)[-1]
                    q_parts = q_path.strip("/").split("/")
                    if "status" in q_parts:
                        quoted_tweet_id = q_parts[q_parts.index("status") + 1]
                except Exception:
                    quoted_tweet_id = None

                if quoted_tweet_id:
                    q_url = f"https://x.com/{quoted_username}/status/{quoted_tweet_id}/photo/{quoted_media_index}"
                    quoted_media_urls.append(q_url)
                    quoted_media_index += 1
            else:
                if tweet_id and screen_name:
                    m_url = f"https://x.com/{screen_name}/status/{tweet_id}/photo/{main_media_index}"
                    media_urls.append(m_url)
                    main_media_index += 1

        tweets.append(
            {
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "username": username_slug,
                "screen_name": screen_name,
                "name": display_name,
                "verified": verified,
                "profile_url": profile_url,
                "text": text,
                "created_at": created_at,
                "time_ago": time_ago,
                "retweeted_by": retweeted_by,
                "replying_to": replying_to,
                "reply_count": reply_count,
                "retweet_count": retweet_count,
                "like_count": like_count,
                "view_count": view_count,
                "media_urls": media_urls,
                "quoted_media_urls": quoted_media_urls,
                "quoted_tweet_url": quoted_tweet_url,
                "quoted_username": quoted_username,
                "quoted_name": quoted_display_name,
                "quoted_text": quoted_text,
            }
        )

        page_tweet_count += 1

    logger.info(f"📄 Nitter tweet search - parsed {page_tweet_count} tweets on this page")

    # Get next page URL via helper (if any)
    next_cursor = None
    next_page_url = get_next_page_url_from_soup(soup)
    if next_page_url:
        logger.info(f"➡️ Next page URL from HTML: {next_page_url}")
        parsed = urlparse(next_page_url)
        qs = parse_qs(parsed.query)
        cursor_vals = qs.get("cursor")
        if cursor_vals:
            next_cursor = cursor_vals[0]
            logger.info(f"🔁 Next cursor: {next_cursor}")
        else:
            logger.info("⏹ No cursor found in next page URL.")
    else:
        logger.info("⏹ No 'Load more' URL found - this is the last page.")

    # Return only this page's tweets and the cursor for the next page
    return {
        "tweets": tweets,
        "next_cursor": next_cursor,
    }


@router.get("/search_people")
async def search_people(
    query: str = Query(..., description="Search people query (via Nitter HTML)"),
    cursor: str = Query(None, description="Pagination cursor (from previous response)"),
):
    """
    Search for people on X (Twitter) using Nitter HTML, one page at a time.
    
    - Each request returns only the results on the current page.
    - If there is another page, a `next_cursor` is returned.
    - The client can pass that `next_cursor` back in the next request to get the next page.
    """
    logger.info(f"🌐 /twitter/search_people (Nitter) - query='{query}', cursor='{cursor}'")

    base_params = {
        "f": "users",
        "q": query,
    }

    # Build params for this page
    params = dict(base_params)
    if cursor:
        params["cursor"] = cursor

    logger.info(f"🔎 Nitter people search - fetching page with params={params}")

    proxies = get_next_nitter_proxy()
    logger.info(f"🌐 Using Nitter proxy (people): {proxies['http']}")

    try:
        response = curl_requests.get(
            "https://nitter.net/search",
            params=params,
            impersonate="chrome",
            proxies=proxies,
        )
    except Exception as e:
        logger.error(f"❌ Error calling Nitter: {e}")
        raise HTTPException(status_code=502, detail="Error contacting Nitter for people search")

    html = response.text

    # Log a snippet of the raw HTML so we can see what Nitter returns in deployment
    logger.info(
        "🌐 Nitter raw HTML (people) length=%s, snippet=%r",
        len(html),
        html[:500],
        "resonse status code", response.status_code
    )
    soup = BeautifulSoup(html, "html.parser")

    users: List[Dict[str, Any]] = []
    page_user_count = 0

    for item in soup.select("div.timeline-item[data-username]"):
        username_slug = item.get("data-username")
        header = item.select_one("div.tweet-header")
        if not header:
                    continue

        # Handle / X screen name
        profile_link_tag = header.select_one("a.username")
        handle_text = profile_link_tag.get_text(strip=True) if profile_link_tag else None  # e.g. "@KwesiFCB"
        if handle_text and handle_text.startswith("@"):
            screen_name = handle_text[1:]
        else:
            screen_name = username_slug

        # X profile and photo URLs
        profile_url = f"https://x.com/{screen_name}" if screen_name else None
        avatar_url = f"https://x.com/{screen_name}/photo" if screen_name else None

        # Name (display name) - use title attribute to avoid verified icon text
        fullname_tag = header.select_one("a.fullname")
        if fullname_tag and fullname_tag.get("title"):
            name = fullname_tag.get("title")
        else:
            name = fullname_tag.get_text(strip=True) if fullname_tag else None

        # Verified badge
        verified = bool(header.select_one(".verified-icon"))

        # Description (bio)
        bio_tag = item.select_one("div.tweet-content.media-body")
        description = bio_tag.get_text(" ", strip=True) if bio_tag else None

        users.append(
            {
                "username": username_slug,    # slug without @
                "name": name,                 # display name
                "verified": verified,
                "description": description,
                "profile_url": profile_url,   # e.g. https://x.com/pyquantnews
                "avatar_url": avatar_url,     # e.g. https://x.com/pyquantnews/photo
            }
        )

        page_user_count += 1

    logger.info(f"📄 Nitter people search - parsed {page_user_count} users on this page")

    # Get next page URL via helper (if any)
    next_cursor = None
    next_page_url = get_next_page_url_from_soup(soup)
    if next_page_url:
        logger.info(f"➡️ Next page URL from HTML: {next_page_url}")
        parsed = urlparse(next_page_url)
        qs = parse_qs(parsed.query)
        cursor_vals = qs.get("cursor")
        if cursor_vals:
            next_cursor = cursor_vals[0]
            logger.info(f"🔁 Next cursor: {next_cursor}")
        else:
            logger.info("⏹ No cursor found in next page URL.")
    else:
        logger.info("⏹ No 'Load more' URL found - this is the last page.")

    # Return only this page's users and the cursor for the next page
    return {
        "users": users,
        "next_cursor": next_cursor,
    }


# @router.get("/search_people")
# async def search_people(
#     query: str = Query(..., description="search query"),
#     cursor: str = Query(None, description="pagination cursor (from previous response)")
# ):
#     account_res = []
#     cookies = {
#         'guest_id': '173823245631103789',
#         'kdt': '6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W',
#         'auth_token': '9a623f0e722ac5d8362860ab368c5d04c0649464',
#         'ct0': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'twid': 'u%3D1663936852208898049',
#         'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
#         'lang': 'en',
#         'guest_id_marketing': 'v1%3A173823245631103789',
#         'guest_id_ads': 'v1%3A173823245631103789',
#         'personalization_id': '"v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#     }

#     headers = {
#         'accept': '*/*',
#         'accept-language': 'en-US,en;q=0.9',
#         'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
#         'content-type': 'application/json',
#         # 'cookie': 'guest_id=173823245631103789; kdt=6bjd9isM3Cdo2ayvkdn7SnKjivMvo2g5pvTIJe9W; auth_token=9a623f0e722ac5d8362860ab368c5d04c0649464; ct0=8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4; twid=u%3D1663936852208898049; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; lang=en; guest_id_marketing=v1%3A173823245631103789; guest_id_ads=v1%3A173823245631103789; personalization_id="v1_RsxMNDt0m7rr8fbAaEvvXQ=="',
#         'priority': 'u=1, i',
#         'referer': 'https://x.com/search?q=(%22AI%20agent%22%20OR%20%22open%20source%22%20OR%20%22LLM%22%20OR%20%22Large%20language%20model%22%20OR%20%22Agentic%22)%20-is%3Aretweet%20lang%3Aen%20since%3A2024-12-30%20until%3A2024-12-31%20min_faves%3A50%20min_retweets%3A10%20-filter%3Areplies&src=typed_query&f=user',
#         'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Brave";v="132"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Linux"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'sec-gpc': '1',
#         'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
#         'x-client-transaction-id': 'gikStOe1Fv43ifqYbVglRNp5ibfykFnAe4T4n+v6egcfYHiT1yafobsRZAeRuHFIEWR49YFyOtA6jkiRvJcHarnVKB2LgQ',
#         'x-client-uuid': '9f4dfd05-5b66-4fe5-ac75-c6910297f088',
#         'x-csrf-token': '8fb44ade4e79858f801721dd0a850180a87f6df28b5ee3f08d0505afba52eb477558761af3cd218c430a54962fe93c10f59cc50535d0fcc77560d228b98058fc53267029f8dd315f5fd30972505f12e4',
#         'x-twitter-active-user': 'yes',
#         'x-twitter-auth-type': 'OAuth2Session',
#         'x-twitter-client-language': 'en',
#     }
#     search_query = query

#     # Define the GraphQL variables
#     graphql_variables = {
#         "rawQuery": search_query,
#         "count": 100,
#         "querySource": "typed_query",
#         "product": "People",
#     }
    
#     # Add cursor if provided
#     if cursor:
#         graphql_variables["cursor"] = cursor
#         print(f"Using provided cursor for people search: {cursor}")

#     # Define the feature flags
#     features = {
#         "profile_label_improvements_pcf_label_in_post_enabled": True,
#         "rweb_tipjar_consumption_enabled": True,
#         "responsive_web_graphql_exclude_directive_enabled": True,
#         "verified_phone_label_enabled": False,
#         "creator_subscriptions_tweet_preview_api_enabled": True,
#         "responsive_web_graphql_timeline_navigation_enabled": True,
#         "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
#         "premium_content_api_read_enabled": False,
#         "communities_web_enable_tweet_community_results_fetch": True,
#         "c9s_tweet_anatomy_moderator_badge_enabled": True,
#         "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
#         "responsive_web_grok_analyze_post_followups_enabled": True,
#         "responsive_web_jetfuel_frame": False,
#         "responsive_web_grok_share_attachment_enabled": True,
#         "articles_preview_enabled": True,
#         "responsive_web_edit_tweet_api_enabled": True,
#         "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
#         "view_counts_everywhere_api_enabled": True,
#         "longform_notetweets_consumption_enabled": True,
#         "responsive_web_twitter_article_tweet_consumption_enabled": True,
#         "tweet_awards_web_tipping_enabled": False,
#         "responsive_web_grok_analysis_button_from_backend": True,
#         "creator_subscriptions_quote_tweet_preview_enabled": False,
#         "freedom_of_speech_not_reach_fetch_enabled": True,
#         "standardized_nudges_misinfo": True,
#         "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
#         "rweb_video_timestamps_enabled": True,
#         "longform_notetweets_rich_text_read_enabled": True,
#         "longform_notetweets_inline_media_enabled": True,
#         "responsive_web_grok_image_annotation_enabled": False,
#         "responsive_web_enhance_cards_enabled": False,
#     }

#     # Construct the request URL
#     base_url = "https://x.com/i/api/graphql/U3QTLwGF8sZCHDuWIMSAmg/SearchTimeline"
#     params = {
#         "variables": json.dumps(graphql_variables),
#         "features": json.dumps(features),
#     }

#     # Make the request
#     response = requests.get(base_url, cookies=cookies, headers=headers, params=params)

#     print("this is the response", response.text)
#     try:
#         data = response.json()
#     except:
#         raise HTTPException(status_code=500, detail="Could not extract accounts from Twitter API response")
    
#     # Extract accounts from response
#     try:
#         accounts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][1]["entries"]
#     except:
#         try:
#             accounts = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"][0]["entries"]
#         except:
#             raise HTTPException(status_code=500, detail="Could not extract accounts from Twitter API response")
    
#     # Extract cursor for next page (Bottom cursor)
#     next_cursor = None
#     for entry in accounts:
#         if entry.get("content", {}).get("entryType") == "TimelineTimelineCursor":
#             cursor_type = entry["content"].get("cursorType")
#             if cursor_type == "Bottom":
#                 next_cursor = entry["content"]["value"]
#                 break
#     if next_cursor:
#         print(f"Next cursor for people search: {next_cursor}")
    
#     # Filter out cursor entries from accounts processing
#     actual_accounts = [entry for entry in accounts if entry.get("content", {}).get("entryType") != "TimelineTimelineCursor"]
    
#     for account in actual_accounts:
#         try:
#             username = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["screen_name"]
#             # print(username)
#             account_url = f'https://x.com/{username}/'
#             name = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["name"]
#             description = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["description"]
#             followers = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["followers_count"]
#             following = account["content"]["itemContent"]["user_results"]["result"]["legacy"]["friends_count"]

#             data = {
#                 "name": name,
#                 "description": description,
#                 "followers_count": followers,
#                 "following_count": following,
#                 "url": account_url
#             }
#             account_res.append(data)
#         except:
#             continue
    
#     # Return results with pagination info
#     return {
#         "accounts": account_res,
#         "next_cursor": next_cursor,
#         "has_more": next_cursor is not None,
#         "total_results": len(account_res)
#     }

def extract_list_id(list_identifier: str) -> str:
    """
    Extract list ID from Twitter list URL or return the ID if already provided.
    
    Args:
        list_identifier: Either a list ID or a Twitter list URL
        
    Returns:
        The extracted list ID or None if invalid
    """
    import re
    
    # If it's already just a numeric ID, return it
    if list_identifier.isdigit():
        return list_identifier
    
    # Extract ID from various Twitter list URL formats
    patterns = [
        r'x\.com/i/lists/(\d+)',  # https://x.com/i/lists/123456789/members
        r'twitter\.com/i/lists/(\d+)',  # https://twitter.com/i/lists/123456789/members
        r'x\.com/i/lists/(\d+)/members',  # https://x.com/i/lists/123456789/members
        r'twitter\.com/i/lists/(\d+)/members',  # https://twitter.com/i/lists/123456789/members
    ]
    
    for pattern in patterns:
        match = re.search(pattern, list_identifier)
        if match:
            return match.group(1)
    
    return None

@router.get("/list_members")
async def get_list_members(
    background_tasks: BackgroundTasks,
    list_identifier: str = Query(..., description="Twitter list ID or URL (e.g., '123456789' or 'https://x.com/i/lists/123456789/members')")
):
    """
    Start a background task to fetch all members from a Twitter list.
    
    This endpoint starts a background task that fetches all members from a specified Twitter list 
    with detailed user information including profile stats, verification status, and engagement metrics.
    
    **Accepts either:**
    - **List ID**: `"1052973537944694784"`
    - **List URL**: `"https://x.com/i/lists/1052973537944694784/members"`
    - **List URL**: `"https://twitter.com/i/lists/1052973537944694784/members"`
    
    The endpoint automatically extracts the list ID from URLs if provided.
    Fetches 500 members per request for optimal performance.
    
    Returns a task ID that can be used to check status and get results.
    """
    try:
        # Extract list ID from URL or use provided ID
        list_id = extract_list_id(list_identifier)
        if not list_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid list identifier. Please provide a valid list ID or URL."
            )
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create task status
        tasks[task_id] = ListMembersStatus(
            task_id=task_id,
            status="pending",
            progress=0,
            message=f"Queued list members extraction for list: {list_id}",
            list_id=list_id,
            total_members=0,
            pages_processed=0,
            current_page=0,
            last_updated=datetime.now().isoformat()
        )
        
        # Add background task (fixed count of 500)
        background_tasks.add_task(extract_list_members_task, task_id, list_id)
        
        # Return immediately
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "List members extraction task queued successfully",
            "list_id": list_id,
            "count_per_page": 500,
            "status_url": f"/twitter/status/{task_id}",
            "results_url": f"/twitter/results/{task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting list members task: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

def extract_list_members_sync(task_id: str, list_id: str):
    """Synchronous function to extract list members (runs in thread pool)"""
    try:
        # Update task status to running
        tasks[task_id].status = "running"
        tasks[task_id].message = "Starting list members extraction..."
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        logger.info(f"Starting list members extraction for task {task_id}, list {list_id}")
        
        # Twitter API cookies and headers
        cookies = {
            'lang': 'en',
            'd_prefs': 'MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw',
            '__cuid': '0641e7de0ab64a19964c03df938b0571',
            'guest_id': 'v1%3A175743256753373750',
            'guest_id_marketing': 'v1%3A175743256753373750',
            'guest_id_ads': 'v1%3A175743256753373750',
            'personalization_id': '"v1_bwkKlUxg9tTwgq7OVjylwg=="',
            'kdt': 'qEbFPOJ1tsbEt2w4Qo69kLrJ0e9eAgRP7kEAbNo4',
            'auth_token': '69248fd51827479cdd467e9921fa2281238eb37b',
            'ct0': '19e5b5f5430e77535fdc6a16d603ec712318f480c3dcfcae5da2bc912ba01f3396fff23ed660e3a456391cecfad3787a60ac9e1090195e463ea5c51d7e1bdb4c5146083c41370b7effb0c9ef99d804d3',
            'twid': 'u%3D897727759358853123',
            '__cf_bm': '_.X5raIz8cSu_xzDM26HM4.6Sl5AC88u7CKv0czHp70-1757787375-1.0.1.1-Z518cqh5qZNAhUWv_jUOADYIJIooPbKsTNX2xx628l48c6uzvzxJkKjZH3tov90Z_shmSpGeClFFHK9arJrVPjZJQNIlytcWyijr0z5wCFo',
        }

        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.7',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
            'content-type': 'application/json',
            'priority': 'u=1, i',
            'referer': f'https://x.com/i/lists/{list_id}/members',
            'sec-ch-ua': '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'x-client-transaction-id': '4rEs7KQ6g9HoXaqekLjl41TdzrOqseFIWPzo701ijxlj9L+wSffo473+Wya1YBC5cKewlOaMqtR/YyySEeXBkidN5e774Q',
            'x-csrf-token': '19e5b5f5430e77535fdc6a16d603ec712318f480c3dcfcae5da2bc912ba01f3396fff23ed660e3a456391cecfad3787a60ac9e1090195e463ea5c51d7e1bdb4c5146083c41370b7effb0c9ef99d804d3',
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
            'x-xp-forwarded-for': '7d5392235ff6128773514b9278153067fbd7a0dcd687a00e98b2705522b0dfc3baf295c7ea652a8f56aa4aea37da4d070fa46eb6025cf57356eafb3545ed075eda55cf927a89e28bc061e444c198a1639f515325c1b6827d149e49ffcbd17cc893e7a2177615a176ac1b2b46298858109946a13bf40bb2e10cc6872e538e99babdd331309bfec5000468f5bd919c3649fbb50935d5f2a28ce92fde3fa1d6038faeb6b661e96521a564cda0c34cf336b85a1731f10e3811fd4e6f689a677cbaacf36800ce2d8fd3d11db707ed89c1de674332a52e63665f089c423c475accd09ee8f9a32efe3535d8d520fb15b86aae6510852104fc2a22d5fda0926b59a8944b04',
        }

        # Initial request parameters (fixed count of 500)
        params = {
            'variables': json.dumps({"listId": list_id, "count": 500}),
            'features': '{"rweb_video_screen_enabled":false,"payments_enabled":false,"profile_label_improvements_pcf_label_in_post_enabled":true,"rweb_tipjar_consumption_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"premium_content_api_read_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"responsive_web_grok_analyze_button_fetch_trends_enabled":false,"responsive_web_grok_analyze_post_followups_enabled":true,"responsive_web_jetfuel_frame":true,"responsive_web_grok_share_attachment_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"responsive_web_grok_show_grok_translated_post":true,"responsive_web_grok_analysis_button_from_backend":true,"creator_subscriptions_quote_tweet_preview_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_grok_image_annotation_enabled":true,"responsive_web_grok_imagine_annotation_enabled":true,"responsive_web_grok_community_note_auto_translation_is_enabled":false,"responsive_web_enhance_cards_enabled":false}',
        }

        # Make initial request
        response = requests.get(
            'https://x.com/i/api/graphql/DBsxqYmf80LvtzMsmWYTKA/ListMembers',
            params=params,
            cookies=cookies,
            headers=headers,
        )

        if response.status_code != 200:
            tasks[task_id].status = "failed"
            tasks[task_id].message = f"Failed to fetch list members. Twitter API returned status {response.status_code}"
            tasks[task_id].last_updated = datetime.now().isoformat()
            return

        # Extract initial members
        response_data = response.json()
        all_members = extract_user_info(response_data)
        
        # Update task with first page results
        tasks[task_id].total_members = len(all_members)
        tasks[task_id].pages_processed = 1
        tasks[task_id].current_page = 1
        tasks[task_id].progress = 10
        tasks[task_id].message = f"Fetched {len(all_members)} members from first page"
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        # Store results in task
        tasks[task_id].results = all_members
        
        # If no members found on first page, mark as completed
        if len(all_members) == 0:
            tasks[task_id].status = "completed"
            tasks[task_id].message = "No members found in the list. The list might be empty, private, or not accessible."
            tasks[task_id].last_updated = datetime.now().isoformat()
            return
        
        # Handle pagination - exactly like the original script
        final = False
        request_count = 0
        
        while True:
            try:
                try:
                    cursor = response.json()['data']['list']['members_timeline']['timeline']['instructions'][2]['entries'][-2]['content']['value']
                except:
                    cursor = response.json()['data']['list']['members_timeline']['timeline']['instructions'][0]['entries'][-2]['content']['value']
            except:
                final = True
                break
            
            # Update parameters with cursor (fixed count of 500)
            params['variables'] = json.dumps({"listId": list_id, "count": 500, "cursor": cursor})
            
            # Make next request
            response = requests.get(
                'https://x.com/i/api/graphql/DBsxqYmf80LvtzMsmWYTKA/ListMembers',
                params=params,
                cookies=cookies,
                headers=headers,
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch page {request_count + 2}: {response.status_code}")
                break
            
            # Extract members from this page
            page_members = extract_user_info(response.json())
            all_members.extend(page_members)
            request_count += 1
            
            # Update task progress
            tasks[task_id].total_members = len(all_members)
            tasks[task_id].pages_processed = request_count + 1
            tasks[task_id].current_page = request_count + 1
            tasks[task_id].progress = min(90, 10 + (request_count * 5))  # Progress up to 90%
            tasks[task_id].message = f"Fetched {len(page_members)} members from page {request_count + 1}. Total: {len(all_members)}"
            tasks[task_id].results = all_members
            tasks[task_id].last_updated = datetime.now().isoformat()
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
            if final:
                break
        
        # Mark task as completed
        tasks[task_id].status = "completed"
        tasks[task_id].progress = 100
        tasks[task_id].message = f"Successfully extracted {len(all_members)} members from list {list_id} across {request_count + 1} pages"
        tasks[task_id].last_updated = datetime.now().isoformat()
        
        logger.info(f"✅ Task {task_id} completed: {len(all_members)} members extracted")
        
    except Exception as e:
        logger.error(f"Error in background task {task_id}: {str(e)}")
        tasks[task_id].status = "failed"
        tasks[task_id].message = f"Task failed: {str(e)}"
        tasks[task_id].last_updated = datetime.now().isoformat()

async def extract_list_members_task(task_id: str, list_id: str):
    """Async wrapper for the background task"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        await loop.run_in_executor(executor, extract_list_members_sync, task_id, list_id)

@router.get("/status/{task_id}")
async def get_twitter_task_status(task_id: str):
    """Get the status of any Twitter background task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    return tasks[task_id]

@router.get("/results/{task_id}")
async def get_twitter_task_results(
    task_id: str,
    page: int = Query(1, description="Page number", ge=1),
    per_page: int = Query(50, description="Items per page", ge=1, le=100)
):
    """Get paginated results of any completed Twitter background task"""
    if task_id not in tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found"
        )
    
    task = tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} is not completed yet. Status: {task.status}"
        )
    
    # Get results from task
    all_results = getattr(task, 'results', [])
    
    # Calculate pagination
    total_items = len(all_results)
    total_pages = (total_items + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    # Get page items
    page_results = all_results[start_idx:end_idx]
    
    # Determine result type based on task type
    result_type = "members" if hasattr(task, 'list_id') else "items"
    result_key = "members" if hasattr(task, 'list_id') else "items"
    
    response = {
        "task_id": task_id,
        "total_items": total_items,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
        result_key: page_results,
        "pagination": {
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None
        }
    }
    
    # Add specific fields based on task type
    if hasattr(task, 'list_id'):
        response["list_id"] = task.list_id
        response["total_members"] = total_items
    
    return response

def extract_user_info(twitter_data):
    """
    Extract important user information from Twitter list JSON data.
    
    Args:
        twitter_data: The JSON data from Twitter API
        
    Returns:
        List of dictionaries containing user information
    """
    users = []
    
    try:
        # Navigate to the entries in the JSON structure
        try:
            entries = twitter_data['data']['list']['members_timeline']['timeline']['instructions'][0]['entries']
            logger.info(f"Found entries in instructions[0], count: {len(entries)}")
        except:
            try:
                entries = twitter_data['data']['list']['members_timeline']['timeline']['instructions'][2]['entries']
                logger.info(f"Found entries in instructions[2], count: {len(entries)}")
            except:
                try:
                    entries = twitter_data['data']['list']['members_timeline']['timeline']['instructions'][1]['entries']
                    logger.info(f"Found entries in instructions[1], count: {len(entries)}")
                except:
                    logger.warning("No entries found in any instructions")
                    return []
                
        for entry in entries:
            if entry.get('content', {}).get('entryType') == 'TimelineTimelineItem':
                user_data = entry['content']['itemContent']['user_results']['result']
                
                # Extract basic information
                user_info = {
                    'user_id': user_data.get('rest_id'),
                    'username': user_data.get('core', {}).get('screen_name'),
                    'display_name': user_data.get('core', {}).get('name'),
                    'created_at': user_data.get('core', {}).get('created_at'),
                    'profile_image': user_data.get('avatar', {}).get('image_url'),
                    'description': user_data.get('legacy', {}).get('description', ''),
                    'location': user_data.get('location', {}).get('location', ''),
                    'website_url': user_data.get('legacy', {}).get('url', ''),
                    
                    # Statistics
                    'followers_count': user_data.get('legacy', {}).get('followers_count', 0),
                    'following_count': user_data.get('legacy', {}).get('friends_count', 0),
                    'tweets_count': user_data.get('legacy', {}).get('statuses_count', 0),
                    'likes_count': user_data.get('legacy', {}).get('favourites_count', 0),
                    'listed_count': user_data.get('legacy', {}).get('listed_count', 0),
                    'media_count': user_data.get('legacy', {}).get('media_count', 0),
                    
                    # Verification and status
                    'verified': user_data.get('verification', {}).get('verified', False),
                    'blue_verified': user_data.get('is_blue_verified', False),
                    'protected': user_data.get('privacy', {}).get('protected', False),
                    'has_graduated_access': user_data.get('has_graduated_access', False),
                    
                    # Profile settings
                    'default_profile': user_data.get('legacy', {}).get('default_profile', True),
                    'default_profile_image': user_data.get('legacy', {}).get('default_profile_image', True),
                    'profile_image_shape': user_data.get('profile_image_shape', 'Circle'),
                    
                    # DM permissions
                    'can_dm': user_data.get('dm_permissions', {}).get('can_dm', False),
                    'can_dm_on_xchat': user_data.get('dm_permissions', {}).get('can_dm_on_xchat', False),
                    
                    # Media permissions
                    'can_media_tag': user_data.get('media_permissions', {}).get('can_media_tag', False),
                    
                    # Relationship info
                    'following_me': user_data.get('relationship_perspectives', {}).get('following', False),
                    
                    # Additional info
                    'is_translator': user_data.get('legacy', {}).get('is_translator', False),
                    'has_custom_timelines': user_data.get('legacy', {}).get('has_custom_timelines', False),
                    'want_retweets': user_data.get('legacy', {}).get('want_retweets', True),
                    'possibly_sensitive': user_data.get('legacy', {}).get('possibly_sensitive', False),
                    
                    # Pinned tweets
                    'pinned_tweet_ids': user_data.get('legacy', {}).get('pinned_tweet_ids_str', []),
                    
                    # Profile interstitial type
                    'profile_interstitial_type': user_data.get('legacy', {}).get('profile_interstitial_type', ''),
                    
                    # Withheld countries
                    'withheld_in_countries': user_data.get('legacy', {}).get('withheld_in_countries', []),
                }
                
                # Add calculated fields
                user_info['account_age_days'] = calculate_account_age(user_info['created_at'])
                user_info['engagement_ratio'] = calculate_engagement_ratio(
                    user_info['followers_count'], 
                    user_info['following_count']
                )
                user_info['tweet_frequency'] = calculate_tweet_frequency(
                    user_info['tweets_count'], 
                    user_info['account_age_days']
                )
                
                users.append(user_info)
                
    except (KeyError, TypeError) as e:
        logger.error(f"Error extracting user data: {e}")
        return []
    
    return users

def calculate_account_age(created_at):
    """Calculate account age in days."""
    if not created_at:
        return 0
    
    try:
        # Parse Twitter's date format: "Fri Sep 22 06:30:47 +0000 2023"
        created_date = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        now = datetime.now(created_date.tzinfo)
        return (now - created_date).days
    except ValueError:
        return 0

def calculate_engagement_ratio(followers, following):
    """Calculate follower to following ratio."""
    if following == 0:
        return 999999.0 if followers > 0 else 0  # Use large number instead of inf for JSON compatibility
    return round(followers / following, 2)

def calculate_tweet_frequency(tweets, account_age_days):
    """Calculate average tweets per day."""
    if account_age_days == 0:
        return 0
    return round(tweets / account_age_days, 2)

