from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, Tuple
import logging
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Country code to name mapping (ISO 3166-1 numeric)
COUNTRY_CODES = {
    840: "United States", 356: "India", 360: "Indonesia", 826: "United Kingdom",
    124: "Canada", 250: "France", 586: "Pakistan", 504: "Morocco", 276: "Germany",
    32: "Argentina", 36: "Australia", 76: "Brazil", 566: "Nigeria", 528: "Netherlands",
    756: "Switzerland", 608: "Philippines", 724: "Spain", 380: "Italy", 818: "Egypt",
    616: "Poland", 170: "Colombia", 752: "Sweden", 458: "Malaysia", 784: "United Arab Emirates",
    704: "Vietnam", 372: "Ireland", 702: "Singapore", 554: "New Zealand", 484: "Mexico",
    578: "Norway", 710: "South Africa", 376: "Israel", 792: "Turkey", 368: "Iraq",
    50: "Bangladesh", 348: "Hungary", 496: "Mongolia", 203: "Czech Republic", 246: "Finland",
    410: "Korea, Republic of", 604: "Peru", 440: "Lithuania", 764: "Thailand", 208: "Denmark",
    12: "Algeria", 392: "Japan", 344: "Hong Kong", 804: "Ukraine", 56: "Belgium",
    620: "Portugal", 158: "Taiwan", 40: "Austria", 100: "Bulgaria", 688: "Serbia",
    800: "Uganda", 218: "Ecuador", 682: "Saudi Arabia", 231: "Ethiopia", 703: "Slovakia",
    300: "Greece", 634: "Qatar", 384: "Côte d'Ivoire", 642: "Romania", 398: "Kazakhstan",
    414: "Kuwait", 788: "Tunisia", 191: "Croatia", 288: "Ghana", 116: "Cambodia",
    512: "Oman", 860: "Uzbekistan", 404: "Kenya", 268: "Georgia", 51: "Armenia",
    196: "Cyprus", 144: "Sri Lanka", 600: "Paraguay", 480: "Mauritius", 222: "El Salvador",
    591: "Panama", 152: "Chile", 862: "Venezuela", 999: "Global"
}

cookies = {
    'sgID': '5f74ab5f-b67b-40ee-9220-25588c5bd559',
    'FPID': 'FPID2.2.urGkWvKFFYrKmDX037AsMSelkWjaObZk04Ox0ciY2j0%3D.1753205096',
    '_pk_id.1.fd33': 'da5a87b63ea7bb72.1764972131.',
    'locale': 'en-us',
    'sw_reg_params': 'action%3Dwebsite_performance%26domain%3Dbito.ai',
    '_tt_enable_cookie': '1',
    '_ttp': '01KBR8KRVEZXBAGM8M753VRC2B_.tt.1',
    'Hm_lvt_427c0b22bf914797e3b57a7be7db74fe': '1764972160',
    '_gcl_au': '1.1.1347053729.1764972162',
    'FPAU': '1.1.1347053729.1764972162',
    'FPLC': 'ipvY8kmkpV2YNR9WF5ISwCGycZqBtqjNbdvehHTxb6me0aNlR3q38p3xlI%2Fv44aWC43oR9ZrPG87t2ge8UPEBpR3dswv5hangq0b8xe8RIvO2nv6yvcDcaHA2rZWSQ%3D%3D',
    'RESET_PRO_CACHE': 'True',
    '.DEVICETOKEN.SIMILARWEB.COM': 'loxdrHEH68lE54qLem6Fihwy9oDTKnXP',
    '.SGTOKEN.SIMILARWEB.COM': 'KnobxMGB6l2e6sm6esbM5yxEwHmxzV04L58hNP1STP844XawgbpcWmIXBLrgyuTojn9ykAen19HpXxGwGYrBQgD64p_RSRJninw6IhWniHMR7sJ6wciJSCSvI-tjDxtCoeRfEI-ABFaFASqWquTxEHK0jZ9gB0BdwKRIjDleuSqU9KMBiuk9dtsCt5NnCkgL0BUj7gksincvKLlNNjeNedoe7nwjWNF4-H32cjdmSfGZc00YeKDmiPrHeWCho_oecsYu8HGlWO4yxEpZ9Uk5Hks1HkQ4FVNLDtEoy8B_oYjcuAOqT7kLdgbQoAPtY1W8LFwrHbAdS4tTIh6Mig-OZV9lp95pcn7NxhINPB1E1oqrIy-ubwe52hH1SJF1mxpv_VeRPC6BrDSO1PHkdAHkUusLIqRHx8eITlCVjoxRaidBgf-sNA2Gk7WO7f-z5jbUn9KWVe1SUMQBfXLj3vp_KZaSvqS8kRGwcwV8DTde1MVzRWNx3_7k_aTLX6GPeKBjUexz28Su7mfIh_u4X6YkI-AWm9x6_rt8bI5oJpzrqu7tQHJXcU9yV6wAVNTdMxmF',
    '_sw_pin': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzODM0ODYxNiIsInRpZCI6IjEwOTIxNTQzIiwicHN0IjoiMSIsInFuIjoiLlNHVE9LRU4uU0lNSUxBUldFQi5DT00iLCJxaCI6ImEzNTE2ZTZlZDRiZTdhYjBhYjVmYTZlOTQ2YmU2MDc4IiwibmJmIjoxNzY0OTcyMTY4LCJleHAiOjE3NjQ5NzU3NjgsImlhdCI6MTc2NDk3MjE2OCwiaXNzIjoiaHR0cHM6Ly9zZWN1cmUuc2ltaWxhcndlYi5jb20ifQ.TsBZmLty_ak25CVGH8dgulKrEd1CBKxuHS0eNDatGRVGMQAH9J7mKmGEeMl4HJdpkq4bWCWgHYo-ioCdXmJz1Z4gP5fiqrwQgkL9vshvfam4Q9yjc4UctFawwkWkyrvLdGbDshAnDYwdLI0Wgqp943zWr2rvFrCJouD1oozA3dw3Db2JgY6ECsLkG4Z8d4nk9eCh8QuJK3p-gAQa6tOi3Ni-H5UGTIuDEuA58zALcUFL5cncz-T90IyNMh977wtwQld9YHWH0l67MdwD4IhM7JNf8zZ_ufwtuBWXE7n8hlNDzl_2Npr_E49LCCTtFZwv2zQReQw7cKsgzrM4rRXsgA',
    '_sw_pin_ps': '1',
    'ph_phc_q6DoVWUpv1bnAsRARtEnObJ0ckrWnM3AjChLhIiKNES_posthog': '%7B%22distinct_id%22%3A%22019af089-5c77-7435-9036-fdb65e1abdcb%22%2C%22%24sesid%22%3A%5B1764972169840%2C%22019af089-5c7d-7540-b413-3623bbe3be23%22%2C1764972125305%5D%2C%22%24initial_person_info%22%3A%7B%22r%22%3A%22%24direct%22%2C%22u%22%3A%22https%3A%2F%2Fwww.similarweb.com%2F%22%7D%7D',
    '_gid': 'GA1.2.1083192767.1764972177',
    'vv_visitor_id': 'loYZ6U4Qmr4au37ghaLDpkJtXn3LTeZ',
    '_BEAMER_USER_ID_zBwGJEbQ32550': '8355585c-1b81-4324-b192-7840d86d8ae0',
    '_BEAMER_FIRST_VISIT_zBwGJEbQ32550': '2025-12-05T22:02:58.110Z',
    '_otor': '1764972178239.https%3A%2F%2Faccount.similarweb.com%2F',
    '_BEAMER_LAST_UPDATE_zBwGJEbQ32550': '1764972311856',
    '_pk_ses.1.fd33': '1',
    'fsrndidpro': 'false',
    '_ga': 'GA1.1.1463411095.1753205096',
    '_ga_V5DSP51YD0': 'GS2.1.s1765015018$o3$g0$t1765015018$j60$l0$h2535423',
    'gtmIdnts': '%7B%22ga_fpid%22%3A%221463411095.1753205096%22%2C%22ga_session_id%22%3A%221765015018%22%2C%22ga_cid%22%3A%221463411095.1753205096%22%2C%22ttp%22%3A%2201KBR8KRVEZXBAGM8M753VRC2B_.tt.1%22%7D',
    'FPGSID': '1.1765015019.1765015019.G-V5DSP51YD0.kN739K5M7Y76IXy2ZxKINA',
    '_BEAMER_FILTER_BY_URL_zBwGJEbQ32550': 'true',
    '_BEAMER_FILTER_BY_URL_zBwGJEbQ32550': 'true',
    '_gat': '1',
    '_gat_oldTracker': '1',
    'vv_session_id': 'SBFmzs7barVIBViYgGHI4fGgTIGJaZjeBM3Q8m1EHAkFkw',
    '_ga_JKZGLE7YPK': 'GS2.2.s1765015023$o2$g0$t1765015023$j60$l0$h0',
    '_clck': '9c8d5b%5E2%5Eg1m%5E0%5E2165',
    'aws-waf-token': 'fba4d4db-2e92-4845-9ef2-4384df718f7b:HQoAhP9EVdkjAAAA:ADWkk8f0EKGKxKS9WECIe7kwQecz338+d79FpgQHCCIpffcIWqsUGv+6rS71HEfPNAfgYHfeXEac8nI91p8zkJqdQdIGs/hDPNfpe5mL0dG6opwwzJI0iI7rMnbQl9I7ifwpoqWfU4tzd/NSbirDuu04tdC/Q5o4vlgoOj/+6HKLOHl75EOVlUBhYtjfGCcM/nAUz+8PdZYk14lnTKS7UOz2KfhxUBJpeaSwbUIWYdNEhplZEMv99VxDrR3M089i6F9ytNLWkELn',
    'ip4': '143.105.209.245',
    'ip6': '2c0f%3A2a80%3A6ba%3A8408%3Ae488%3A32b7%3A7d82%3A8a0c',
    '_otr': '1765015023617.https%3A%2F%2Fwww.similarweb.com%2F',
    '_ots': '1.1765015023617.1765015023617.1765015023617',
    '_otui': '1040424237.1764972178239.1764972178239.1765015023617.2.2.0',
    '_otpe': 'https%3A%2F%2Fpro.similarweb.com%2F%23%2Fdigitalsuite%2Fhome',
    '_clsk': '14xu5dz%5E1765015026486%5E1%5E1%5El.clarity.ms%2Fcollect',
    '__q_state_9u7uiM39FyWVMWQF': 'eyJ1dWlkIjoiOGJjZWI3OWMtYTc3Mi00OWYyLWE2ZWEtY2QzY2NiOGExYWFhIiwiY29va2llRG9tYWluIjoic2ltaWxhcndlYi5jb20iLCJtZXNzZW5nZXJFeHBhbmRlZCI6ZmFsc2UsInByb21wdERpc21pc3NlZCI6ZmFsc2UsImNvbnZlcnNhdGlvbklkIjoiMTgwMDIwMDYxOTYxOTQ2MDI1NCJ9',
    'ttcsid': '1765015023225::z4PVbMgF1_iQ0jPrJMGg.2.1765015064144.0',
    'ttcsid_CP7J3T3C77U51N36SHN0': '1765015023225::beGgCHco9aK0cyRc-JpI.2.1765015064144.0',
    '_dd_s': 'rum=0&expire=1765015978290',
    '_ga_V5DSP51YD': 'GS2.1.s1765015015$o4$g1$t1765015078$j60$l0$h0',
    'mp_7ccb86f5c2939026a4b5de83b5971ed9_mixpanel': '%7B%22distinct_id%22%3A%2238348616%22%2C%22%24device_id%22%3A%225f17e826-34e4-49b3-8557-c09a5357b50c%22%2C%22User%20Agent%22%3A%22Mozilla%2F5.0%20(Macintosh%3B%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F142.0.0.0%20Safari%2F537.36%22%2C%22sgId%22%3A%225f74ab5f-b67b-40ee-9220-25588c5bd559%22%2C%22site_type%22%3A%22Pro%22%2C%22session_id%22%3A%22016dcfef-5c12-473e-930a-42864ec8d53f%22%2C%22session_first_event_time%22%3A%222025-12-06T09%3A56%3A59.482Z%22%2C%22url%22%3A%22https%3A%2F%2Fpro.similarweb.com%2F%23%2Fdigitalsuite%2Fhome%22%2C%22is_sw_user%22%3Afalse%2C%22language%22%3A%22en-us%22%2C%22sw_extention%22%3Afalse%2C%22last_event_time%22%3A1765015078302%2C%22%24initial_referrer%22%3A%22%24direct%22%2C%22%24initial_referring_domain%22%3A%22%24direct%22%2C%22__mps%22%3A%7B%7D%2C%22__mpso%22%3A%7B%7D%2C%22__mpus%22%3A%7B%7D%2C%22__mpa%22%3A%7B%7D%2C%22__mpu%22%3A%7B%7D%2C%22__mpr%22%3A%5B%5D%2C%22__mpap%22%3A%5B%5D%2C%22%24user_id%22%3A%2238348616%22%2C%22ui_generation%22%3A%2220251205.81581.9e20c55%22%2C%22page_id%22%3A%22digitalsuite-homepage-%22%2C%22sidebar_version%22%3A%223.1%22%2C%22subscription_id%22%3A%2210000090%22%2C%22base_product%22%3A%22Competitive%20Intelligence%20After%20Trial%22%2C%22user_id%22%3A38348616%2C%22account_id%22%3A10921543%2C%22email%22%3A%22marriondokosi%40gmail.com%22%2C%22role%22%3A%22AccountAdmin%22%2C%22CustomUserPersona%22%3A2%2C%22si_extension%22%3Afalse%2C%22section%22%3A%22digitalsuite%22%2C%22sub_section%22%3A%22homepage%22%2C%22sub_sub_section%22%3A%22%22%2C%22date_range_mode%22%3Anull%2C%22max_history%22%3Anull%2C%22entity_id%22%3A%22%22%2C%22entity_name%22%3A%22%22%2C%22ab_test_name%22%3A%22GB-hwx-2235-new-compare-btn-text%22%2C%22ab_test_value%22%3A%22Control%22%7D',
    '_uetsid': '1dbd5060d22611f0829767bd9a226378',
    '_uetvid': '1dbd65b0d22611f08a945da39e827f80',
}

def get_previous_month_dates() -> Tuple[str, str]:
    """
    Get the first and last day of the previous month in 'YYYY|MM|DD' format.
    
    Returns:
        Tuple of (from_date, to_date) strings
    """
    today = datetime.now()
    # Get first day of current month
    first_day_current = today.replace(day=1)
    # Get last day of previous month
    last_day_previous = first_day_current - timedelta(days=1)
    # Get first day of previous month
    first_day_previous = last_day_previous.replace(day=1)
    
    from_date = first_day_previous.strftime('%Y|%m|%d')
    to_date = last_day_previous.strftime('%Y|%m|%d')
    
    return from_date, to_date

def get_base_headers(page_view_id: str = 'b6826fe7-c2b5-4fa2-9a64-ce34ffa02452') -> Dict[str, str]:
    """Get base headers with optional page view ID"""
    return {
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json; charset=utf-8',
        'priority': 'u=1, i',
        'referer': 'https://pro.similarweb.com/',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        'x-sw-page': 'https://pro.similarweb.com/#/digitalsuite/websiteanalysis/overview/website-performance/*/999/1m?key=arcads.ai',
        'x-sw-page-view-id': page_view_id,
    }

def get_website_data(domain: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch and structure website data from SimilarWeb API.
    
    Args:
        domain: The domain to analyze (e.g., 'arcads.ai')
        from_date: Start date in format 'YYYY|MM|DD' (defaults to first day of previous month)
        to_date: End date in format 'YYYY|MM|DD' (defaults to last day of previous month)
    
    Returns:
        Unified structured data dictionary
    """
    # If dates not provided, use previous month's first and last day
    if from_date is None or to_date is None:
        prev_from, prev_to = get_previous_month_dates()
        from_date = from_date or prev_from
        to_date = to_date or prev_to
    # Initialize unified structure
    unified_data = {
        "domain": domain,
        "metadata": {},
        "rankings": {},
        "traffic": {},
        "engagement": {},
        "trafficSources": {},
        "geography": {},
        "referrals": {},
        "competitors": [],
        "dateRange": {
            "from": from_date.replace('|', '-'),
            "to": to_date.replace('|', '-'),
            "granularity": "Monthly"
        }
    }
    
    # 1. Get header data (basic info)
    headers = get_base_headers()
    params = {
        'keys': domain,
        'mainDomainOnly': 'true',
        'includeCrossData': 'true',
    }
    response = requests.get(
        'https://pro.similarweb.com/api/WebsiteOverview/getheader',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    header_data = response.json()
    
    if domain in header_data:
        site_data = header_data[domain]
        unified_data["metadata"] = {
            "title": site_data.get("title", ""),
            "description": site_data.get("description", ""),
            "icon": site_data.get("icon", ""),
            "image": site_data.get("image", ""),
            "imageLarge": site_data.get("imageLarge", ""),
            "category": site_data.get("category", ""),
            "employeeRange": site_data.get("employeeRange", ""),
            "hasGaToken": site_data.get("hasGaToken", False),
            "privacyStatus": site_data.get("privacyStatus", "None")
        }
        unified_data["rankings"]["global"] = {
            "rank": site_data.get("globalRanking", 0),
            "trend": []
        }
        unified_data["rankings"]["country"] = {
            "rank": site_data.get("highestTrafficCountryRanking", 0),
            "countryCode": site_data.get("highestTrafficCountry", 0),
            "countryName": COUNTRY_CODES.get(site_data.get("highestTrafficCountry", 0), "Unknown"),
            "trend": []
        }
        unified_data["rankings"]["category"] = {
            "rank": site_data.get("categoryRanking", 0),
            "category": site_data.get("category", ""),
            "trend": []
        }
        unified_data["traffic"]["monthlyVisits"] = site_data.get("monthlyVisits", 0)
    
    # 2. Get geography data
    headers = get_base_headers('776568a0-4e1c-4bd3-969e-f36c384340a9')
    params = {
        'country': '999',
        'mainDomainOnly': 'true',
        'includeCrossData': 'true',
        'keys': domain,
        'pageSize': '5',
        'from': from_date,
        'to': to_date,
        'isWindow': 'false',
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteGeography/Geography/Table',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    geo_data = response.json()
    
    if "Data" in geo_data and isinstance(geo_data["Data"], list):
        unified_data["geography"]["topCountries"] = []
        for country_data in geo_data["Data"]:
            country_code = country_data.get("Country", 0)
            unified_data["geography"]["topCountries"].append({
                "countryCode": country_code,
                "countryName": COUNTRY_CODES.get(country_code, f"Country {country_code}"),
                "share": country_data.get("Share", 0),
                "usersShare": country_data.get("UsersShare", 0),
                "rank": country_data.get("Rank", 0),
                "change": country_data.get("Change", 0),
                "avgVisitDuration": country_data.get("AvgVisitDuration", 0),
                "pagesPerVisit": country_data.get("PagePerVisit", 0),
                "bounceRate": country_data.get("BounceRate", 0)
            })
        unified_data["geography"]["totalCountries"] = geo_data.get("TotalCount", 0)
    
    # 3. Get similar sites (competitors)
    headers = get_base_headers('3dfedaf0-875f-48ea-a2d0-37b7c7209573')
    params = {
        'key': domain,
        'limit': '5',
    }
    response = requests.get(
        'https://pro.similarweb.com/api/WebsiteOverview/getsimilarsites',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    similar_data = response.json()
    
    if isinstance(similar_data, list):
        unified_data["competitors"] = [
            {
                "domain": site.get("Domain", ""),
                "rank": site.get("Rank", 0),
                "favicon": site.get("Favicon", "")
            }
            for site in similar_data
        ]
    
    # 4. Get desktop vs mobile visits
    headers = get_base_headers('72df4a2e-8e51-4c5f-b1df-4f7701628fb0')
    params = {
        'country': '999',
        'from': from_date,
        'to': to_date,
        'includeSubDomains': 'true',
        'isWindow': 'false',
        'keys': domain,
        'timeGranularity': 'Monthly',
        'webSource': 'Total',
        'ShouldGetVerifiedData': 'false',
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverview/EngagementDesktopVsMobileVisits/PieChart',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    device_data = response.json()
    
    if "Data" in device_data and domain in device_data["Data"]:
        device_info = device_data["Data"][domain]
        desktop = device_info.get("Desktop", 0)
        mobile = device_info.get("Mobile Web", 0)
        total = desktop + mobile
        unified_data["traffic"]["deviceSplit"] = {
            "desktop": desktop,
            "mobile": mobile,
            "desktopPercentage": round((desktop / total * 100) if total > 0 else 0, 2),
            "mobilePercentage": round((mobile / total * 100) if total > 0 else 0, 2)
        }
    
    # 5. Get engagement overview
    headers = get_base_headers('e38c147b-3e50-48b6-858b-5236a2a9593b')
    params = {
        'country': '999',
        'iso': '[object Object]',
        'to': to_date,
        'from': from_date,
        'isWindow': 'false',
        'webSource': 'Total',
        'ignoreFilterConsistency': 'false',
        'includeSubDomains': 'true',
        'timeGranularity': 'Monthly',
        'keys': domain,
        'ShouldGetVerifiedData': 'false',
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverview/EngagementOverview/Table',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    engagement_data = response.json()
    
    if "Data" in engagement_data and isinstance(engagement_data["Data"], list) and len(engagement_data["Data"]) > 0:
        eng = engagement_data["Data"][0]
        unified_data["engagement"]["avgVisitDuration"] = eng.get("AvgVisitDuration", 0)
        unified_data["engagement"]["pagesPerVisit"] = eng.get("PagesPerVisit", 0)
        unified_data["engagement"]["bounceRate"] = eng.get("BounceRate", 0)
        unified_data["engagement"]["totalPageViews"] = eng.get("TotalPagesViews", 0)
        unified_data["traffic"]["totalVisits"] = eng.get("AvgMonthVisits", 0)
    
    # 6. Get traffic sources breakdown
    headers = get_base_headers('f365ccd9-025d-437d-8fef-d7f2dbde5468')
    params = {
        'country': '999',
        'from': from_date,
        'to': to_date,
        'includeSubDomains': 'true',
        'isWindow': 'false',
        'timeGranularity': 'Monthly',
        'keys': domain,
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/MarketingMixTotal/TrafficSourcesOverview/PieChart',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    sources_data = response.json()
    
    if "Data" in sources_data and "Total" in sources_data["Data"] and domain in sources_data["Data"]["Total"]:
        total_sources = sources_data["Data"]["Total"][domain]
        unified_data["trafficSources"]["total"] = {
            "organicSearch": total_sources.get("Organic Search", 0),
            "direct": total_sources.get("Direct", 0),
            "social": total_sources.get("Social", 0),
            "paidSearch": total_sources.get("Paid Search", 0),
            "referrals": total_sources.get("Referrals", 0),
            "displayAds": total_sources.get("Display Ads", 0),
            "email": total_sources.get("Email", 0)
        }
        
        if "Desktop" in sources_data["Data"] and domain in sources_data["Data"]["Desktop"]:
            desktop_sources = sources_data["Data"]["Desktop"][domain]
            unified_data["trafficSources"]["desktop"] = {
                "organicSearch": desktop_sources.get("Organic Search", 0),
                "direct": desktop_sources.get("Direct", 0),
                "social": desktop_sources.get("Social", 0),
                "paidSearch": desktop_sources.get("Paid Search", 0),
                "referrals": desktop_sources.get("Referrals", 0),
                "displayAds": desktop_sources.get("Display Ads", 0),
                "email": desktop_sources.get("Email", 0)
            }
        
        if "MobileWeb" in sources_data["Data"] and domain in sources_data["Data"]["MobileWeb"]:
            mobile_sources = sources_data["Data"]["MobileWeb"][domain]
            unified_data["trafficSources"]["mobile"] = {
                "organicSearch": mobile_sources.get("Organic Search", 0),
                "direct": mobile_sources.get("Direct", 0),
                "social": mobile_sources.get("Social", 0),
                "paidSearch": mobile_sources.get("Paid Search", 0),
                "referrals": mobile_sources.get("Referrals", 0),
                "displayAds": mobile_sources.get("Display Ads", 0),
                "email": mobile_sources.get("Email", 0)
            }
    
    # 7. Get top referrals (incoming)
    headers = get_base_headers('19936c38-93d1-4b5b-bdbf-ca17d6737cba')
    params = {
        'country': '999',
        'from': from_date,
        'includeSubDomains': 'true',
        'isWindow': 'false',
        'keys': domain,
        'timeGranularity': 'Monthly',
        'to': to_date,
        'pageSize': '5',
        'webSource': 'Desktop',
        'orderBy': 'TotalShare desc',
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverviewDesktop/TopReferrals/Table',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    referrals_data = response.json()
    
    if "Data" in referrals_data and isinstance(referrals_data["Data"], list):
        unified_data["referrals"]["incoming"] = [
            {
                "domain": ref.get("Domain", ""),
                "share": ref.get("Share", 0),
                "change": ref.get("Change", 0),
                "category": ref.get("Category", "")
            }
            for ref in referrals_data["Data"]
        ]
    
    # 8. Get traffic destination referrals (outgoing)
    headers = get_base_headers('36d3f4ab-1dda-4cd5-9721-4ea6bbc3027f')
    params = {
        'appMode': 'single',
        'country': '999',
        'from': from_date,
        'includeSubDomains': 'true',
        'isWindow': 'false',
        'keys': domain,
        'timeGranularity': 'Monthly',
        'to': to_date,
        'pageSize': '5',
        'webSource': 'Desktop',
        'orderBy': 'TotalShare desc',
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverviewDesktop/TrafficDestinationReferrals/Table',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    destinations_data = response.json()
    
    if "Data" in destinations_data and isinstance(destinations_data["Data"], list):
        unified_data["referrals"]["outgoing"] = [
            {
                "domain": dest.get("Domain", ""),
                "share": dest.get("Share", 0),
                "change": dest.get("Change", 0),
                "category": dest.get("Category", "-")
            }
            for dest in destinations_data["Data"]
        ]
    
    # 9. Get social media breakdown
    headers = get_base_headers('5ce8802f-8ec1-4e7a-9919-4c6235aa835f')
    params = {
        'country': '999',
        'includeSubDomains': 'true',
        'webSource': 'Desktop',
        'timeGranularity': 'Monthly',
        'from': from_date,
        'to': to_date,
        'isWindow': 'false',
        'keys': domain,
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverviewDesktop/TrafficSourcesSocial/PieChart',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    social_data = response.json()
    
    if "Data" in social_data and domain in social_data["Data"]:
        social_info = social_data["Data"][domain]
        unified_data["trafficSources"]["socialBreakdown"] = {}
        total_social = unified_data["trafficSources"]["total"].get("social", 0)
        
        for platform, data in social_info.items():
            if isinstance(data, dict) and "Share" in data:
                share = data.get("Share", 0)
                unified_data["trafficSources"]["socialBreakdown"][platform.lower()] = {
                    "share": share,
                    "visits": round(total_social * share, 2) if total_social > 0 else 0
                }
    
    # 10. Get total visits metric
    headers = get_base_headers('800efbf7-d152-434d-9269-4d4dc8255d9b')
    params = {
        'country': '999',
        'from': from_date,
        'to': to_date,
        'includeSubDomains': 'true',
        'isWindow': 'false',
        'keys': domain,
        'timeGranularity': 'Monthly',
        'webSource': 'Total',
        'ShouldGetVerifiedData': 'false',
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverview/EngagementVisits/SingleMetric',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    visits_data = response.json()
    
    if "Data" in visits_data and domain in visits_data["Data"]:
        visits_info = visits_data["Data"][domain]
        unified_data["traffic"]["totalVisits"] = visits_info.get("TotalVisits", 0)
        unified_data["traffic"]["change"] = visits_info.get("Change", 0)
        unified_data["traffic"]["trend"] = visits_info.get("Trend", [])
    
    # 11. Get web ranks
    headers = get_base_headers('3283c830-6658-466e-a927-3d68897c67ed')
    params = {
        'country': '999',
        'includeSubDomains': 'true',
        'webSource': 'Total',
        'timeGranularity': 'Monthly',
        'from': from_date,
        'to': to_date,
        'isWindow': 'false',
        'keys': domain,
    }
    response = requests.get(
        'https://pro.similarweb.com/widgetApi/WebsiteOverview/WebRanks/SingleMetric',
        params=params,
        cookies=cookies,
        headers=headers,
    )
    ranks_data = response.json()
    
    if "Data" in ranks_data and domain in ranks_data["Data"]:
        ranks_info = ranks_data["Data"][domain]
        
        if "GlobalRank" in ranks_info:
            unified_data["rankings"]["global"]["rank"] = ranks_info["GlobalRank"].get("Value", 0)
            unified_data["rankings"]["global"]["trend"] = [
                {"date": item.get("Key", ""), "value": item.get("Value", 0)}
                for item in ranks_info["GlobalRank"].get("Trend", [])
            ]
        
        if "CountryRank" in ranks_info:
            unified_data["rankings"]["country"]["rank"] = ranks_info["CountryRank"].get("Value", 0)
            unified_data["rankings"]["country"]["trend"] = [
                {"date": item.get("Key", ""), "value": item.get("Value", 0)}
                for item in ranks_info["CountryRank"].get("Trend", [])
            ]
        
        if "CategoryRank" in ranks_info:
            unified_data["rankings"]["category"]["rank"] = ranks_info["CategoryRank"].get("Value", 0)
            unified_data["rankings"]["category"]["trend"] = [
                {"date": item.get("Key", ""), "value": item.get("Value", 0)}
                for item in ranks_info["CategoryRank"].get("Trend", [])
            ]
    
    return unified_data


@router.get("/website-info")
async def get_website_info(
    domain: str = Query(..., description="Domain to analyze (e.g., 'arcads.ai')"),
    from_date: Optional[str] = Query(None, description="Start date in format 'YYYY|MM|DD' (defaults to first day of previous month)"),
    to_date: Optional[str] = Query(None, description="End date in format 'YYYY|MM|DD' (defaults to last day of previous month)")
) -> Dict[str, Any]:
    """
    Get comprehensive website analytics data from SimilarWeb.
    
    Returns unified structured data including:
    - Metadata (title, description, category, etc.)
    - Rankings (global, country, category)
    - Traffic metrics (visits, device split, trends)
    - Engagement metrics (duration, pages per visit, bounce rate)
    - Traffic sources (organic, direct, social, paid, etc.)
    - Geography (top countries with engagement metrics)
    - Referrals (incoming and outgoing)
    - Competitors (similar sites)
    
    Args:
        domain: The domain to analyze
        from_date: Optional start date (defaults to previous month's first day)
        to_date: Optional end date (defaults to previous month's last day)
    
    Returns:
        Unified structured website data dictionary
    """
    try:
        logger.info(f"Fetching SimilarWeb data for domain: {domain}")
        
        # Get website data
        result = get_website_data(domain, from_date, to_date)
        
        if not result or not result.get("domain"):
            logger.info(f"No data found for domain: {domain}")
            return {}
        
        # Check if we have meaningful non-zero data
        traffic = result.get("traffic", {})
        rankings = result.get("rankings", {})
        engagement = result.get("engagement", {})
        geography = result.get("geography", {})
        referrals = result.get("referrals", {})
        competitors = result.get("competitors", [])
        
        # Check for meaningful traffic data
        has_traffic = (
            traffic.get("totalVisits", 0) > 0 or
            traffic.get("monthlyVisits", 0) > 0
        )
        
        # Check for meaningful rankings
        has_rankings = (
            rankings.get("global", {}).get("rank", 0) > 0 or
            rankings.get("country", {}).get("rank", 0) > 0 or
            rankings.get("category", {}).get("rank", 0) > 0
        )
        
        # Check for meaningful engagement
        has_engagement = (
            engagement.get("avgVisitDuration", 0) > 0 or
            engagement.get("pagesPerVisit", 0) > 0 or
            engagement.get("totalPageViews", 0) > 0
        )
        
        # Check for geography data
        has_geography = (
            len(geography.get("topCountries", [])) > 0 or
            geography.get("totalCountries", 0) > 0
        )
        
        # Check for referrals
        has_referrals = (
            len(referrals.get("incoming", [])) > 0 or
            len(referrals.get("outgoing", [])) > 0
        )
        
        # Check for competitors
        has_competitors = len(competitors) > 0
        
        # If all meaningful data is zero/empty, return empty dict
        has_meaningful_data = (
            has_traffic or
            has_rankings or
            has_engagement or
            has_geography or
            has_referrals or
            has_competitors
        )
        
        if not has_meaningful_data:
            logger.info(f"No meaningful data found for domain: {domain} (all metrics are zero/empty)")
            return {}
        
        logger.info(f"Successfully fetched data for {domain}")
        return JSONResponse(content=result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching SimilarWeb data for {domain}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching website data: {str(e)}"
        )
