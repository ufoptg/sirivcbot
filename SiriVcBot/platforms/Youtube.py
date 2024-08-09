import asyncio
import os
import re
from typing import Union

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

from SiriVcBot.utils.database import is_on_off
from SiriVcBot.utils.formatters import time_to_seconds

# Define the scopes required for YouTube Data API access
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def authenticate_youtube():
    """Handles the OAuth2 authentication process."""
    credentials = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '/home/vm/sirivcbot/SiriVcBot/credentials.json', SCOPES)

            # For headless environments, provide instructions
            try:
                credentials = flow.run_local_server(port=0)
            except Exception as e:
                # In case run_local_server fails, provide manual instructions
                print("Running in a headless environment.")
                auth_url, _ = flow.authorization_url()
                print("Visit this URL in your browser to authorize the application:")
                print(auth_url)
                code = input("Enter the authorization code here: ")
                credentials = flow.fetch_token(code=code)

        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return credentials

class YouTubeAPI:
    def __init__(self):
        # Initialize the YouTube API client
        self.youtube = build('youtube', 'v3', credentials=authenticate_youtube())
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
    
    async def exists(self, link: str, videoid: Union[bool, str] = None):
        """Check if a YouTube link is valid."""
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        """Extract URL from a message."""
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def search_video(self, query):
        """Search for a video on YouTube."""
        try:
            request = self.youtube.search().list(
                part="snippet",
                maxResults=1,
                q=query
            )
            response = request.execute()

            if response['items']:
                video = response['items'][0]
                title = video['snippet']['title']
                vidid = video['id']['videoId']
                thumbnail = video['snippet']['thumbnails']['high']['url']
                duration_min = self.get_video_duration(vidid)
                return title, duration_min, thumbnail, vidid
        except HttpError as e:
            print(f"An error occurred: {e}")
            return None
    
    def get_video_duration(self, video_id):
        """Get the duration of a video using its ID."""
        try:
            request = self.youtube.videos().list(
                part="contentDetails",
                id=video_id
            )
            response = request.execute()
            duration = response['items'][0]['contentDetails']['duration']
            return self.convert_duration(duration)
        except HttpError as e:
            print(f"An error occurred: {e}")
            return None

    def convert_duration(self, duration):
        """Convert YouTube's ISO 8601 duration to minutes."""
        match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
        hours = int(match.group(1)[:-1]) if match.group(1) else 0
        minutes = int(match.group(2)[:-1]) if match.group(2) else 0
        seconds = int(match.group(3)[:-1]) if match.group(3) else 0
        total_minutes = hours * 60 + minutes + seconds / 60
        return total_minutes

    async def details(self, query):
        """Fetch video details including title, duration, and thumbnail."""
        title, duration_min, thumbnail, vidid = await self.search_video(query)
        duration_sec = int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, query):
        """Get the title of a video."""
        title, _, _, _ = await self.search_video(query)
        return title

    async def duration(self, query):
        """Get the duration of a video."""
        _, duration_min, _, _ = await self.search_video(query)
        return duration_min

    async def thumbnail(self, query):
        """Get the thumbnail URL of a video."""
        _, _, thumbnail, _ = await self.search_video(query)
        return thumbnail

    async def video(self, query):
        """Get the video URL."""
        _, _, _, vidid = await self.search_video(query)
        video_url = f"https://www.youtube.com/watch?v={vidid}"
        return video_url

    async def track(self, query):
        """Fetch detailed track information."""
        title, duration_min, thumbnail, vidid = await self.search_video(query)
        yturl = f"https://www.youtube.com/watch?v={vidid}"
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def download(self, link: str, video: Union[bool, str] = None):
        """Download a video using yt-dlp."""
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_optssx = {
                "format": "bestaudio[ext=m4a]",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        def video_dl():
            ydl_optssx = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                return xyz
            x.download([link])
            return xyz

        if video:
            if await is_on_off(1):
                direct = True
                downloaded_file = await loop.run_in_executor(None, video_dl)
            else:
                proc = await asyncio.create_subprocess_exec(
                    "yt-dlp",
                    "-g",
                    "-f",
                    "best[height<=?720][width<=?1280]",
                    f"{link}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    downloaded_file = stdout.decode().split("\n")[0]
                    direct = None
                else:
                    return
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        return downloaded_file, direct

# Example usage of YouTubeAPI in a Telegram bot handler

async def handle_youtube_query(query: str):
    yt_api = YouTubeAPI()
    video_url = await yt_api.video(query)
    print(f"Found video URL: {video_url}")

if __name__ == '__main__':
    # Test the API with a sample query
    asyncio.run(handle_youtube_query("Rick Astley Never Gonna Give You Up"))
