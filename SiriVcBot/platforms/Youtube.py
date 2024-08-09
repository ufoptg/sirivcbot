import asyncio
import os
import re
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from SiriVcBot.utils.database import is_on_off
from SiriVcBot.utils.formatters import time_to_seconds
from Spotify import SpotifyAPI  # Assuming Spotify.py has a class named SpotifyAPI


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.cookies_file = os.path.join(os.path.dirname(__file__), "youtube_cookies.txt")  # Assuming cookies are in the same directory
        self.spotify_api = SpotifyAPI()  # Initialize the Spotify API for fallback

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
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
        return text[offset:offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration_min = result["duration"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                vidid = result["id"]
                duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
            return title, duration_min, duration_sec, thumbnail, vidid
        except Exception as e:
            print(f"Error with YouTube: {e}. Falling back to Spotify...")
            return await self.spotify_api.details(link)  # Fallback to Spotify

    async def title(self, link: str, videoid: Union[bool, str] = None):
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
            return title
        except Exception as e:
            print(f"Error with YouTube: {e}. Falling back to Spotify...")
            return await self.spotify_api.title(link)  # Fallback to Spotify

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                duration = result["duration"]
            return duration
        except Exception as e:
            print(f"Error with YouTube: {e}. Falling back to Spotify...")
            return await self.spotify_api.duration(link)  # Fallback to Spotify

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            results = VideosSearch(link, limit=1)
            for result in (await results.next())["result"]:
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            return thumbnail
        except Exception as e:
            print(f"Error with YouTube: {e}. Falling back to Spotify...")
            return await self.spotify_api.thumbnail(link)  # Fallback to Spotify

    async def video(self, link: str, videoid: Union[bool, str] = None):
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "--cookies", self.cookies_file,
                "-g",
                "-f",
                "best[height<=?720][width<=?1280]",
                f"{link}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if stdout:
                return 1, stdout.decode().split("\n")[0]
            else:
                return 0, stderr.decode()
        except Exception as e:
            print(f"Error with YouTube: {e}. Falling back to Spotify...")
            return await self.spotify_api.video(link)  # Fallback to Spotify

    # Implement similar error handling and fallback for other methods...

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        try:
            if videoid:
                link = self.base + link
            loop = asyncio.get_running_loop()

            def audio_dl():
                ydl_optssx = {
                    "format": "bestaudio[ext=m4a]",
                    "outtmpl": "downloads/%(id)s.%(ext)s",
                    "geo_bypass": True,
                    "nocheckcertificate": True,
                    "quiet": True,
                    "no_warnings": True,
                    "cookies": self.cookies_file,
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
                    "cookies": self.cookies_file,
                }
                x = yt_dlp.YoutubeDL(ydl_optssx)
                info = x.extract_info(link, False)
                xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz

            if songvideo:
                await loop.run_in_executor(None, video_dl)
                fpath = f"downloads/{title}.mp4"
                return fpath
            elif songaudio:
                await loop.run_in_executor(None, audio_dl)
                fpath = f"downloads/{title}.mp3"
                return fpath
            elif video:
                if await is_on_off(1):
                    direct = True
                    downloaded_file = await loop.run_in_executor(None, video_dl)
                else:
                    proc = await asyncio.create_subprocess_exec(
                        "yt-dlp",
                        "--cookies", self.cookies_file,
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
        except Exception as e:
            print(f"Error with YouTube download: {e}. Falling back to Spotify...")
            return await self.spotify_api.download(link)  # Fallback to Spotify
