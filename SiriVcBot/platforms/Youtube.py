import asyncio
import os
import re
from typing import Union, Dict
import requests
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message

# Constants
YOUTUBE_API_KEY = 'AIzaSyDQVt8rQcaK97h97hYnzOVBAuTN-G3qq1k'  # Replace with your YouTube API key
YOUTUBE_API_URL = 'https://www.googleapis.com/youtube/v3'

def youtube_api_request(endpoint: str, params: Dict) -> Dict:
    response = requests.get(f"{YOUTUBE_API_URL}/{endpoint}", params=params)
    if response.status_code == 200:
        return response.json()
    return {}

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

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
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
        if offset is None:
            return None
        return text[offset : offset + length]

    async def get_video_info(self, video_id: str) -> Dict:
        params = {
            'part': 'snippet,contentDetails',
            'id': video_id,
            'key': YOUTUBE_API_KEY
        }
        data = youtube_api_request('videos', params)
        if data.get('items'):
            item = data['items'][0]
            snippet = item['snippet']
            content_details = item['contentDetails']
            return {
                'title': snippet.get('title', 'Unknown title'),
                'duration': content_details.get('duration', 'Unknown duration'),
                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'video_id': video_id
            }
        return {}

    async def details(self, link: str, videoid: Union[bool, str] = None) -> Dict[str, Union[str, int]]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        video_id = await self._parse_video_id(link)
        if not video_id:
            return {'error': 'Invalid YouTube link'}
        video_info = await self.get_video_info(video_id)
        return video_info

    async def title(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        video_id = await self._parse_video_id(link)
        if not video_id:
            return 'Invalid YouTube link'
        video_info = await self.get_video_info(video_id)
        return video_info.get('title', 'Unknown title')

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        video_id = await self._parse_video_id(link)
        if not video_id:
            return 'Invalid YouTube link'
        video_info = await self.get_video_info(video_id)
        return video_info.get('duration', 'Unknown duration')

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> str:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        video_id = await self._parse_video_id(link)
        if not video_id:
            return 'Invalid YouTube link'
        video_info = await self.get_video_info(video_id)
        return video_info.get('thumbnail', '')

    async def video(self, link: str, videoid: Union[bool, str] = None) -> Tuple[int, str]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
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
            return 1, stdout.decode().split("\n")[0]
        else:
            return 0, stderr.decode()

    async def playlist(self, link: str, limit: int, user_id: str, videoid: Union[bool, str] = None) -> list:
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        result = [id_ for id_ in playlist.split("\n") if id_]
        return result

    async def track(self, link: str, videoid: Union[bool, str] = None) -> Dict[str, Union[str, int]]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        video_id = await self._parse_video_id(link)
        if not video_id:
            return {'error': 'Invalid YouTube link'}
        video_info = await self.get_video_info(video_id)
        track_details = {
            'title': video_info.get('title', 'Unknown title'),
            'link': video_info.get('url', link),
            'vidid': video_id,
            'duration_min': video_info.get('duration', 'Unknown duration'),
            'thumb': video_info.get('thumbnail', '')
        }
        return track_details

    async def formats(self, link: str, videoid: Union[bool, str] = None) -> Tuple[list, str]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r.get("formats", []):
                try:
                    if "dash" not in format.get("format", "").lower():
                        formats_available.append({
                            "format": format.get("format", ''),
                            "filesize": format.get("filesize", ''),
                            "format_id": format.get("format_id", ''),
                            "ext": format.get("ext", ''),
                            "format_note": format.get("format_note", ''),
                            "yturl": link,
                        })
                except KeyError:
                    continue
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None) -> Tuple[str, str, str, str]:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        video_id = await self._parse_video_id(link)
        if not video_id:
            return 'Invalid YouTube link', '', '', ''
        video_info = await self.get_video_info(video_id)
        title = video_info.get('title', 'Unknown title')
        duration_min = video_info.get('duration', 'Unknown duration')
        thumbnail = video_info.get('thumbnail', '')
        return title, duration_min, thumbnail, video_id

    async def download(self, link: str, mystic, video: Union[bool, str] = None, videoid: Union[bool, str] = None, songaudio: Union[bool, str] = None, songvideo: Union[bool, str] = None, format_id: Union[bool, str] = None, title: Union[bool, str] = None) -> str:
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

        def song_video_dl():
            formats = f"{format_id}+140"
            fpath = f"downloads/{title}"
            ydl_optssx = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_optssx = {
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
            }
            x = yt_dlp.YoutubeDL(ydl_optssx)
            x.download([link])

        if songvideo:
            await loop.run_in_executor(None, song_video_dl)
            fpath = f"downloads/{title}.mp4"
            return fpath
        elif songaudio:
            await loop.run_in_executor(None, song_audio_dl)
            fpath = f"downloads/{title}.mp3"
            return fpath
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
                    return
        else:
            direct = True
            downloaded_file = await loop.run_in_executor(None, audio_dl)
        return downloaded_file, direct

    async def _parse_video_id(self, link: str) -> str:
        if "youtu.be" in link:
            return link.split("youtu.be/")[-1].split('?')[0]
        if "v=" in link:
            return link.split("v=")[-1].split('&')[0]
        return None
