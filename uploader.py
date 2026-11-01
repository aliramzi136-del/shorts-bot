"""رفع وجدولة على يوتيوب (videos.insert = 1600 وحدة quota)."""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import config

def _client():
    creds = Credentials(
        None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def upload(path, script, publish_at_iso):
    tags = script.get("tags", [])
    hashtags = " ".join("#" + t.replace(" ", "") for t in tags[:5])
    body = {
        "snippet": {
            "title": script["title"][:95],
            "description": f"{script.get('description', '')}\n\n#Shorts {hashtags}",
            "tags": tags[:15], "categoryId": config.CATEGORY_ID,
            "defaultLanguage": "ar", "defaultAudioLanguage": "ar",
        },
        # publishAt بيشتغل بس مع private، ويوتيوب بيحوله public في الميعاد
        "status": {"privacyStatus": "private", "publishAt": publish_at_iso,
                   "selfDeclaredMadeForKids": False},
    }
    req = _client().videos().insert(part="snippet,status", body=body,
                                    media_body=MediaFileUpload(path, chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]
