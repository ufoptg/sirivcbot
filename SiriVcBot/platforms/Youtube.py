import asyncio
import os
import re
from typing import Union, Dict, Tuple

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from SiriVcBot.utils.database import is_on_off
from SiriVcBot.utils.formatters import time_to_seconds

# Assuming Spotify-related imports and methods exist
from SiriVcBot.utils.spotify import search_spotify, download_from_spotify  # Replace with actual import

async def shell_cmd(cmd: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    errorz_decoded = errorz.decode("utf-8").lower()
    if "unavailable videos are hidden" in errorz_decoded:
        return out.decode("utf-8")
    elif errorz:
        return errorz.decode("utf-8")
    return out.decode("utf-8")

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(r"(?:youtube\.com|youtu\.be)")
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message: Message) -> Union[str, None]:
        messages = [message]
        if message.reply_to_message:
            messages.append(message.reply_to_message)
        text = ""
        for msg in messages:
            entities = msg.entities or msg.caption_entities
            if entities:
                for entity in entities:
                    if entity.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK]:
                        text = msg.text or msg.caption
                        return text[entity.offset: entity.offset + entity.length]
        return None

    async def _clean_link(self, link: str) -> str:
        if "&" in link:
            link = link.split("&")[0]
        if "?si=" in link:
            link = link.split("?si=")[0]
        return link

    async def details(self, link: str, videoid: Union[bool, str] = None) -> Tuple[str, str, int, str, str]:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        results = VideosSearch(link, limit=1)
        result = (await results.next())["result"][0]
        title = result["title"]
        duration_min = result["duration"]
        thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        vidid = result["id"]
        duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        results = VideosSearch(link, limit=1)
        return (await results.next())["result"][0]["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        results = VideosSearch(link, limit=1)
        return (await results.next())["result"][0]["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        results = VideosSearch(link, limit=1)
        return (await results.next())["result"][0]["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None) -> Tuple[int, str]:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "-g",
                "-f",
                "best[height<=?720][width<=?1280]",
                link,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if stdout:
                return 1, stdout.decode().split("\n")[0]
        except Exception as e:
            print(f"Error occurred: {e}")
            # Fallback to Spotify
            track_details, vidid = await self.track(link)
            spotify_url = await search_spotify(track_details['title'])
            return 0, spotify_url
        return 0, stderr.decode()

    async def playlist(self, link: str, limit: int, videoid: Union[bool, str] = None) -> list:
        if videoid:
            link = self.listbase + link
        link = await self._clean_link(link)
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        return [item for item in playlist.split("\n") if item]

    async def track(self, link: str, videoid: Union[bool, str] = None) -> Tuple[Dict[str, str], str]:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        results = VideosSearch(link, limit=1)
        result = (await results.next())["result"][0]
        track_details = {
            "title": result["title"],
            "link": result["link"],
            "vidid": result["id"],
            "duration_min": result["duration"],
            "thumb": result["thumbnails"][0]["url"].split("?")[0],
        }
        return track_details, result["id"]

    async def formats(self, link: str, videoid: Union[bool, str] = None) -> Tuple[list, str]:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        formats_available = []
        with ydl:
            info = ydl.extract_info(link, download=False)
            for fmt in info.get("formats", []):
                if "dash" in fmt.get("format", "").lower():
                    continue
                formats_available.append({
                    "format": fmt.get("format"),
                    "filesize": fmt.get("filesize"),
                    "format_id": fmt.get("format_id"),
                    "ext": fmt.get("ext"),
                    "format_note": fmt.get("format_note"),
                    "yturl": link,
                })
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None) -> Tuple[str, str, str, str]:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        results = VideosSearch(link, limit=10)
        result = (await results.next())["result"][query_type]
        return (result["title"], result["duration"], result["thumbnails"][0]["url"].split("?")[0], result["id"])

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
    ) -> Tuple[str, Union[None, bool]]:
        if videoid:
            link = self.base + link
        link = await self._clean_link(link)
        loop = asyncio.get_running_loop()

        async def audio_dl() -> str:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = ydl.extract_info(link, False)
            file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(file_path):
                return file_path
            ydl.download([link])
            return file_path

        async def video_dl() -> str:
            ydl_opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = ydl.extract_info(link, False)
            file_path = os.path.join("downloads", f"{info['id']}.{info['ext']}")
            if os.path.exists(file_path):
                return file_path
            ydl.download([link])
            return file_path

        async def song_video_dl() -> None:
            formats = f"{format_id}+140"
            file_path = f"downloads/{title}"
            ydl_opts = {
                "format": formats,
                "outtmpl": file_path,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            ydl.download([link])

        async def song_audio_dl() -> None:
            file_path = f"downloads/{title}.%(ext)s"
            ydl_opts = {
                "format": format_id,
                "outtmpl": file_path,
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
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            ydl.download([link])

        try:
            if songvideo:
                await loop.run_in_executor(None, song_video_dl)
                return f"downloads/{title}.mp4", True
            elif songaudio:
                await loop.run_in_executor(None, song_audio_dl)
                return f"downloads/{title}.mp3", True
            elif video:
                if await is_on_off(1):
                    file_path = await loop.run_in_executor(None, video_dl)
                    return file_path, True
                else:
                    proc = await asyncio.create_subprocess_exec(
                        "yt-dlp",
                        "-g",
                        "-f",
                        "best[height<=?720][width<=?1280]",
                        link,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await proc.communicate()
                    if stdout:
                        return stdout.decode().split("\n")[0], None
                    return None, False
            else:
                file_path = await loop.run_in_executor(None, audio_dl)
                return file_path, True
        except Exception as e:
            print(f"Error occurred during download: {e}")
            # Fallback to Spotify
            track_details, _ = await self.track(link)
            spotify_url = await search_spotify(track_details['title'])
            return spotify_url, False
