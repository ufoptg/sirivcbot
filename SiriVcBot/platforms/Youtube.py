import asyncio
import os
import re
from typing import Union
import yt_dlp
from googleapiclient.discovery import build
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from SiriVcBot.utils.database import is_on_off
from SiriVcBot.utils.formatters import time_to_seconds
import logging

# Replace with your YouTube Data API v3 key
API_KEY = 'AIzaSyDQVt8rQcaK97h97hYnzOVBAuTN-G3qq1k'

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Adjust the logging level as needed
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()  # Optional: output to console
    ]
)
logger = logging.getLogger(__name__)

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.youtube = build('youtube', 'v3', developerKey=API_KEY)
        logger.info("YouTubeAPI initialized with API key")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        exists = bool(re.search(self.regex, link))
        logger.debug(f"Checked existence for link {link}: {exists}")
        return exists

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        url = message.text[entity.offset:entity.offset + entity.length]
                        logger.debug(f"Extracted URL: {url}")
                        return url
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        url = entity.url
                        logger.debug(f"Extracted URL from caption: {url}")
                        return url
        return None

    async def get_video_info(self, video_id: str):
        try:
            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            response = request.execute()
            logger.debug(f"API response for video ID {video_id}: {response}")
            if response.get('items'):
                video = response['items'][0]
                title = video['snippet']['title']
                duration = video['contentDetails']['duration']
                thumbnail = video['snippet']['thumbnails']['high']['url']
                views = video['statistics'].get('viewCount', 'N/A')
                return title, duration, thumbnail, views
            else:
                logger.warning(f"No items found for video ID {video_id}")
                return None
        except Exception as e:
            logger.error(f"Error fetching video info for ID {video_id}: {e}")
            return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        video_id = link.split('v=')[-1].split('&')[0]
        info = await self.get_video_info(video_id)
        if info:
            title, duration, thumbnail, views = info
            duration_sec = int(time_to_seconds(duration)) if duration else 0
            logger.info(f"Video details: Title: {title}, Duration: {duration}, Duration (sec): {duration_sec}, Thumbnail: {thumbnail}, Video ID: {video_id}")
            return title, duration, duration_sec, thumbnail, video_id
        logger.warning(f"Details not found for video ID {video_id}")
        return None

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        video_id = link.split('v=')[-1].split('&')[0]
        info = await self.get_video_info(video_id)
        if info:
            title, _, _, _ = info
            logger.info(f"Video title for ID {video_id}: {title}")
            return title
        logger.warning(f"Title not found for video ID {video_id}")
        return None

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        video_id = link.split('v=')[-1].split('&')[0]
        info = await self.get_video_info(video_id)
        if info:
            _, duration, _, _ = info
            logger.info(f"Video duration for ID {video_id}: {duration}")
            return duration
        logger.warning(f"Duration not found for video ID {video_id}")
        return None

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        video_id = link.split('v=')[-1].split('&')[0]
        info = await self.get_video_info(video_id)
        if info:
            _, _, thumbnail, _ = info
            logger.info(f"Thumbnail URL for video ID {video_id}: {thumbnail}")
            return thumbnail
        logger.warning(f"Thumbnail not found for video ID {video_id}")
        return None

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        try:
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
                url = stdout.decode().split("\n")[0]
                logger.info(f"Video URL fetched: {url}")
                return 1, url
            else:
                error_message = stderr.decode()
                logger.error(f"Error fetching video URL: {error_message}")
                return 0, error_message
        except Exception as e:
            logger.error(f"Exception in video fetch: {e}")
            return 0, str(e)

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        try:
            playlist = await shell_cmd(
                f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
            )
            logger.info(f"Fetched playlist for link {link}: {playlist}")
            return [x for x in playlist.split("\n") if x]
        except Exception as e:
            logger.error(f"Error fetching playlist: {e}")
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        video_id = link.split('v=')[-1].split('&')[0]
        info = await self.get_video_info(video_id)
        if info:
            title, _, thumbnail, _ = info
            track_info = {
                "title": title,
                "link": link,
                "vidid": video_id,
                "duration_min": duration,
                "thumb": thumbnail,
            }
            logger.info(f"Track info for ID {video_id}: {track_info}")
            return track_info, video_id
        logger.warning(f"Track info not found for video ID {video_id}")
        return None

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        ydl_opts = {"quiet": True, "user-agent": "Mozilla/5.0"}
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        try:
            with ydl:
                formats_available = []
                r = ydl.extract_info(link, download=False)
                for format in r["formats"]:
                    if not "dash" in str(format["format"]).lower():
                        formats_available.append(
                            {
                                "format": format["format"],
                                "filesize": format["filesize"],
                                "format_id": format["format_id"],
                                "ext": format["ext"],
                                "format_note": format["format_note"],
                                "yturl": link,
                            }
                        )
                logger.info(f"Formats available for link {link}: {formats_available}")
                return formats_available, link
        except Exception as e:
            logger.error(f"Error fetching formats for link {link}: {e}")
            return str(e), link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        try:
            a = await self.search(link, limit=10)
            result = a.get("result")[query_type]
            slider_result = (result["title"], result["duration"], result["thumbnails"][0]["url"].split("?")[0], result["id"])
            logger.info(f"Slider result: {slider_result}")
            return slider_result
        except Exception as e:
            logger.error(f"Error in slider function for link {link}: {e}")
            return None

    async def download(self, link: str, mystic, video: Union[bool, str] = None, videoid: Union[bool, str] = None, songaudio: Union[bool, str] = None, songvideo: Union[bool, str] = None, format_id: Union[bool, str] = None, title: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "user-agent": "Mozilla/5.0"
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                logger.info(f"Audio file already exists: {xyz}")
                return xyz
            x.download([link])
            logger.info(f"Downloaded audio file: {xyz}")
            return xyz

        def video_dl():
            ydl_opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "user-agent": "Mozilla/5.0"
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            info = x.extract_info(link, False)
            xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(xyz):
                logger.info(f"Video file already exists: {xyz}")
                return xyz
            x.download([link])
            logger.info(f"Downloaded video file: {xyz}")
            return xyz

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_opts = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
                "user-agent": "Mozilla/5.0"
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            x.download([link])
            logger.info(f"Downloaded song video: {fpath}")

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_opts = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "user-agent": "Mozilla/5.0"
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            x.download([link])
            logger.info(f"Downloaded song audio: {fpath}")

        try:
            if songvideo:
                await loop.run_in_executor(None, song_video_dl)
                return f"downloads/{title}.mp4"
            elif songaudio:
                await loop.run_in_executor(None, song_audio_dl)
                return f"downloads/{title}.mp3"
            elif video:
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
                        logger.error(f"Error fetching video URL: {stderr.decode()}")
                        return
            else:
                direct = True
                downloaded_file = await loop.run_in_executor(None, audio_dl)
            logger.info(f"Download complete: {downloaded_file}")
            return downloaded_file, direct
        except Exception as e:
            logger.error(f"Error in download function: {e}")
            return str(e), None
