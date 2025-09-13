import requests
import json
import re

transcript = []

url = 'https://www.youtube.com/watch?v=3cEPgsbIdkw'
url = url.split('&',1)[0]
# print(url)
try:
    response_text = requests.get(url).text
    match = re.search(r'"getTranscriptEndpoint":\{"params":"(.*?)"', response_text)
    if match:
        value = match.group(1)
        # print(value)


    external_video_id = url.split('v=')[1]
    transcript_params = value

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'origin': 'https://www.youtube.com',
        'priority': 'u=1, i',
        'referer': 'https://www.youtube.com/watch?v=sVIZsmdudZM',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-arch': '"arm"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-form-factors': '"Desktop"',
        'sec-ch-ua-full-version': '"140.0.7339.133"',
        'sec-ch-ua-full-version-list': '"Chromium";v="140.0.7339.133", "Not=A?Brand";v="24.0.0.0", "Google Chrome";v="140.0.7339.133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"15.6.1"',
        'sec-ch-ua-wow64': '?0',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'same-origin',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'x-browser-channel': 'stable',
        'x-browser-copyright': 'Copyright 2025 Google LLC. All rights reserved.',
        'x-browser-validation': 'jFliu1AvGMEE7cpr93SSytkZ8D4=',
        'x-browser-year': '2025',
        'x-goog-visitor-id': 'CgtRRm9FWXZMTVVIOCiurpLGBjIKCgJHSBIEGgAgPQ%3D%3D',
        'x-youtube-bootstrap-logged-in': 'false',
        'x-youtube-client-name': '1',
        'x-youtube-client-version': '2.20250911.00.00',
        # 'cookie': 'GPS=1; YSC=ahGoNhJ6LXk; VISITOR_INFO1_LIVE=QFoEYvLMUH8; VISITOR_PRIVACY_METADATA=CgJHSBIEGgAgPQ%3D%3D; __Secure-ROLLOUT_TOKEN=CJiTr_aFwZXDlwEQodye3pvUjwMYrKT-3pvUjwM%3D; PREF=f4=4000000&f6=40000000&tz=Africa.Accra&f7=100',
    }

    params = {
        'prettyPrint': 'false',
    }

    json_data = {
        'context': {
            'client': {
                'hl': 'en',
                'gl': 'GH',
                'remoteHost': '2c0f:2a80:683:e308:5c3f:cda4:b984:2f5d',
                'deviceMake': 'Apple',
                'deviceModel': '',
                'visitorData': 'CgtRRm9FWXZMTVVIOCiurpLGBjIKCgJHSBIEGgAgPQ%3D%3D',
                'userAgent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36,gzip(gfe)',
                'clientName': 'WEB',
                'clientVersion': '2.20250911.00.00',
                'osName': 'Macintosh',
                'osVersion': '10_15_7',
                'originalUrl': 'https://www.youtube.com/?themeRefresh=1',
                'screenPixelDensity': 2,
                'platform': 'DESKTOP',
                'clientFormFactor': 'UNKNOWN_FORM_FACTOR',
                'configInfo': {
                    'appInstallData': 'CK6uksYGENPhrwUQmZixBRCU_rAFENuvrwUQgc3OHBDnr88cEMXWzxwQ79zPHBC52c4cEImwzhwQyfevBRDwnLAFEK7WzxwQppqwBRCr-M4cEIqCgBMQv_fPHBDe6c8cEN68zhwQndCwBRCc188cEOmIzxwQvbauBRCRwc8cELWrgBMQiIewBRCT8s8cEOjkzxwQy9GxBRDN0bEFELfq_hIQ4tSuBRC72c4cEL2KsAUQ_LLOHBDXwbEFEIv3zxwQi-nPHBD2q7AFEL2mgBMQ7MbPHBDgzbEFEOLozxwQieiuBRD7tM8cEMzfrgUQh6zOHBCNzLAFEIKPzxwQ4OnPHBDI988cEO2ogBMQuOTOHBDFw88cEMb3zxwQmY2xBRCYuc8cEL2ZsAUQ0NbPHBDw488cENr3zhwQhefPHBCzkM8cEMWjgBMQk6eAExCVtM8cKkRDQU1TTHhVc29MMndETkhrQnNlVUVyVFE1Z3VQOUE2OF93NjF6QWFIVERLSG1BV2hpd1lEekl3RnYwbkNHY3UzQmgwSDAA',
                    'coldConfigData': 'CK6uksYGEO26rQUQvbauBRDi1K4FEL2KsAUQ8JywBRCd0LAFEM_SsAUQ4_iwBRCkvrEFENfBsQUQr6fOHBD8ss4cEPK2zxwQkcHPHBDsxs8cEPjGzxwQpcrPHBDb088cENDWzxwQnNfPHBDd2c8cEIPazxwQpdzPHBDP3s8cEM_gzxwQsuHPHBDf4s8cEIzozxwQjujPHBCL6c8cEJPyzxwQr_PPHBDy888cEMb3zxwQyPfPHBoyQU9qRm94MlZISWNMV0lwU2RBUm1hT3BuN3p3a1FKLTdZRzF3U0U2TEMyM1k3UFF6TEEiMkFPakZveDJWSEljTFdJcFNkQVJtYU9wbjd6d2tRSi03WUcxd1NFNkxDMjNZN1BRekxBKnxDQU1TV1Ewa3VOMjNBcVFaN3luUUViVUVzaENEaFpvUW5oVDVEdTRBRktzZDJoSC1JNmNOdGdNVk5hYmV0Ui1SbkFYVnhnVHJ3Z1lFcGRJR29hZ0VrNDBGaTRzRnlGcV9SYmdMdmNBR01yY29rTjhHMmFRR0E2S3lCZlV2',
                    'coldHashData': 'CK6uksYGEhM3OTU2OTM0NDE1NDc3Mjk2NzQ0GK6uksYGMjJBT2pGb3gyVkhJY0xXSXBTZEFSbWFPcG43endrUUotN1lHMXdTRTZMQzIzWTdQUXpMQToyQU9qRm94MlZISWNMV0lwU2RBUm1hT3BuN3p3a1FKLTdZRzF3U0U2TEMyM1k3UFF6TEFCfENBTVNXUTBrdU4yM0FxUVo3eW5RRWJVRXNoQ0RoWm9RbmhUNUR1NEFGS3NkMmhILUk2Y050Z01WTmFiZXRSLVJuQVhWeGdUcndnWUVwZElHb2FnRWs0MEZpNHNGeUZxX1JiZ0x2Y0FHTXJjb2tOOEcyYVFHQTZLeUJmVXY%3D',
                    'hotHashData': 'CK6uksYGEhQxMzM2MDgwNjA5MDE3OTY3OTU5NBiurpLGBiiU5PwSKKXQ_RIonpH-EijIyv4SKK_M_hIot-r-EijAg_8SKMeAgBMoioKAEyj3kIATKLWbgBMoxaOAEyjko4ATKIOkgBMopKaAEyi9poATKJOngBMo76eAEyjtqIATKPKqgBMoy6uAEzIyQU9qRm94MlZISWNMV0lwU2RBUm1hT3BuN3p3a1FKLTdZRzF3U0U2TEMyM1k3UFF6TEE6MkFPakZveDJWSEljTFdJcFNkQVJtYU9wbjd6d2tRSi03WUcxd1NFNkxDMjNZN1BRekxBQjRDQU1TSVEwS290ZjZGYTdCQnBOTjhncTVCQlVYM2NfQ0RNYW43UXZZelFtbHdBWFdWdz09',
                },
                'screenDensityFloat': 2,
                'userInterfaceTheme': 'USER_INTERFACE_THEME_DARK',
                'browserName': 'Chrome',
                'browserVersion': '140.0.0.0',
                'acceptHeader': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'deviceExperimentId': 'ChxOelUwT1RNeU5URXdNREk0T0RReU1qTXdNZz09EK6uksYGGK6uksYG',
                'rolloutToken': 'CJiTr_aFwZXDlwEQodye3pvUjwMY44393pvUjwM%3D',
                'screenWidthPoints': 898,
                'screenHeightPoints': 798,
                'utcOffsetMinutes': 0,
                'connectionType': 'CONN_CELLULAR_4G',
                'memoryTotalKbytes': '8000000',
                'mainAppWebInfo': {
                    'graftUrl': 'https://www.youtube.com/watch?v=' + external_video_id,
                    'pwaInstallabilityStatus': 'PWA_INSTALLABILITY_STATUS_UNKNOWN',
                    'webDisplayMode': 'WEB_DISPLAY_MODE_FULLSCREEN',
                    'isWebNativeShareAvailable': True,
                },
                'timeZone': 'Africa/Accra',
            },
            'user': {
                'lockedSafetyMode': False,
            },
            'request': {
                'useSsl': True,
                'internalExperimentFlags': [],
                'consistencyTokenJars': [],
                'attestationResponseData': {
                    'challenge': 'a=6&a2=10&b=CLP7D70FJsl4udTJTzzdDvWx-J4&c=1757714222&d=1&t=7200&c1a=1&c6a=1&c6b=1&hh=NPEYVx8T0Rbbm_Y91a9af6hxRYpiDAbkBI8MJPss1mM',
                    'webResponse': '$qzQ5NGxRAAZj9q_iQ_beA7cuVzmK_kanADQBEArZ1FVoJk1vvEsjc0K-XQLlqEtTdyjUAdnKIHMAGR4G_EemEFC5OyLgLdNa4LBpETD1ngAAADjOAAAACPQBB-IAU4-hQXfm19_2uKj8lIIJwouOyMr6jGztszPOjYmT9RVEoA2AcYJH-agnyWbtURK90mvwUDbzwBUoLP0w-GmcJOxcIpAshoPGYXDpEIw34vD1BlKOBQUAKbqfEXkJhISa9NmypAuaFtGvKe-wFKfIh3dLFcdpiK0kMQzK4yNzshFW1I8UOJ2AgJhZtgFqv2jpW0dA4kIS0hAn-xe3iV5Zk_nf3RR1yEv9b30Z3lIIn7hBB44im5lR5u94ydViHD0oVtHTu_hrZdXXDB0qYqlMVD5YRTSyE8bMIA59N00q4GCvvgOk2pxX22qpD8QdvjF5QRbStTrdQXf2i_rHZ0YEO6jVZQBIaMe_re-HNK-t1jyZnsj7kPEthV1kOmxhzlfxPZ-gdVyZ8RZyrNYOOiHF_GThrSgFTfmwYqd_H0FkNpM9_uppOv8JIntcYtFnPncSat_IHpjAi6AAe9TcBRvzSFRgu7YULSurL8nBuBvqZyuqg3YnhlVjGaYmStoRfKf2oQ-DozkfFuOLFffd9zT2QdrM-EICjyBCJq1P39aqfZ028R3MGzRVtX5S2XCV09LDuX4bXDJfo3Cq6YbipedxZYgaWNTMD9pB1sEy2uxXsqkahhfJhkRqzjXoW4vZpl4BQpES_SC5nhqwmNElOroukub66CYKGcqIuBIUnC5cYEk5ytExsAYd-YlKFznslweHMYKYbKqt0B0pt2sHjIek7JYw5iLv8kildPwKRErpawHoCU_Mknd7GtJFXN85YA6fPMh94FMsFqtB_KblD3-BhGCZR6jwJ25KS5ELxxoC8NXwSQ562XsuXzzEoIr1ESEABmpI0qtrN1vp2GZCrbj03fEY_FlJ8n25Q_VM1_HmqjxT7-ExIaKOroTJJwGMB2tge4mSN0M_NZ0lpQsAE4Ko9fiUG5tQvw2rmWzvKaUtr0oL8Sa4fq21skjApybKnhFZ2KRVAiF9pR5t4cwr59g1sHxuzLmpi5xg59rRYuFgRGRewGynxIzO0Ik0THBPlQJzTD7Bb_1IyeslDIhVyy5MGQV8wetCwQZBIen4Xc-DrxqaiNmtj7iuFo8bhNCpVqvA3E-UIRm1gw6zoCOiMN31JQRQugqbzDgnVwguPYqfgMYcXJfgmdU1mRpY0QlLhrhhK1GjBAX9R1i0mMDHqbrLe7yOLvVmkC5sGeLX_3Pi_4mKjKPcjsXBxJ365csvEyeU0RoTgLVvodkmjGLeklDHzxer1PuD6wccTx0h07aHxLuwF7Fw1TQ6wTOGtuzuYOeaKwHp69X7X3flZ6YG70TX9aOv4T9UDGjpYb47Jpfd05Yx2tphugjfCGYJEJHrgehAHwvxy2CVuW0_yLm3dgqOB2GvrpfwT59BX-yjmCnk_kgYVfH9IoXZANauIsFpjaIk6x5r7mdu-sPR72yYs4Ukr6_3yYcHQQ9Q5962WH24inVYqd0TVpsDfGWBYJQElZqYtfOtHnDkF1rIq4h34Swpo10z6UBUaFD33Isux1zeyo25YXu1-YEuOq-jAc8F_qJG0lEb5fJonhEtmZVeQiWNpOLRgdrfwzPb9Uc5SCQEeJeXaGJGGosYi-yXnwspsyF_SZcfC5ZX4My04AtZpX4nVGS1wwBe0gG47cji8O-tjd3ajWv8sUTqvjaDdg8C_PfHCUDksLh9OnDBZyrtW2d-AckIvtS1cp392bF7KeBwfG24SgM5jYnVKvVKaGe3vbkXf-aspjQ6eP-0Cm0PKVp4QVtoHcssfvjf0XKHhXvJwzxmPwj4yqutR5-XIPvQn77Zq2GhNspadCesmkyokXWQk5NdmvVY3KM',
                },
            },
            'clickTracking': {
                'clickTrackingParams': 'CBEQ040EGAciEwjF4oKLnNSPAxV8VE8EHRH5IzXKAQROZ7Ao',
            },
            'adSignalsInfo': {
                'params': [
                    {
                        'key': 'dt',
                        'value': '1757714223284',
                    },
                    {
                        'key': 'flash',
                        'value': '0',
                    },
                    {
                        'key': 'frm',
                        'value': '0',
                    },
                    {
                        'key': 'u_tz',
                        'value': '0',
                    },
                    {
                        'key': 'u_his',
                        'value': '4',
                    },
                    {
                        'key': 'u_h',
                        'value': '956',
                    },
                    {
                        'key': 'u_w',
                        'value': '1470',
                    },
                    {
                        'key': 'u_ah',
                        'value': '924',
                    },
                    {
                        'key': 'u_aw',
                        'value': '1470',
                    },
                    {
                        'key': 'u_cd',
                        'value': '30',
                    },
                    {
                        'key': 'bc',
                        'value': '31',
                    },
                    {
                        'key': 'bih',
                        'value': '798',
                    },
                    {
                        'key': 'biw',
                        'value': '898',
                    },
                    {
                        'key': 'brdim',
                        'value': '0,158,0,158,1470,32,1470,798,898,798',
                    },
                    {
                        'key': 'vis',
                        'value': '1',
                    },
                    {
                        'key': 'wgl',
                        'value': 'true',
                    },
                    {
                        'key': 'ca_type',
                        'value': 'image',
                    },
                ],
            },
        },
        'params': transcript_params,
        'externalVideoId': external_video_id,
    }

    response = requests.post(
        'https://www.youtube.com/youtubei/v1/get_transcript',
        params=params,
        headers=headers,
        json=json_data,
    )

    # print(response.json())

    for text in response.json()['actions'][0]['updateEngagementPanelAction']['content']['transcriptRenderer']['content']['transcriptSearchPanelRenderer']['body']['transcriptSegmentListRenderer']['initialSegments']:
        try:
            # print(text['transcriptSegmentRenderer']['snippet']['runs'][0]['text'])
            transcript.append(text['transcriptSegmentRenderer']['snippet']['runs'][0]['text'])
        except:
            # print(text['transcriptSectionHeaderRenderer']['sectionHeader']['sectionHeaderViewModel']['headline']['content'])
            transcript.append(text['transcriptSectionHeaderRenderer']['sectionHeader']['sectionHeaderViewModel']['headline']['content'])
        # print('\n')

    print('\n'.join(transcript))
except Exception as e:
    print("transcript not found. ", e)