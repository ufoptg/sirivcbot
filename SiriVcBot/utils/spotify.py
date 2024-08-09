import re
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from youtubesearchpython.__future__ import VideosSearch
import config

class SpotifyAPI:
    def __init__(self):
        self.regex = r"^(https:\/\/open.spotify.com\/)(.*)$"
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.client_secret = config.SPOTIFY_CLIENT_SECRET
        if self.client_id and self.client_secret:
            self.client_credentials_manager = SpotifyClientCredentials(
                self.client_id, self.client_secret
            )
            self.spotify = spotipy.Spotify(
                client_credentials_manager=self.client_credentials_manager
            )
        else:
            self.spotify = None

    async def valid(self, link: str):
        return bool(re.search(self.regex, link))

    async def _run_spotify_func(self, func, *args):
        if self.spotify is None:
            raise ValueError("Spotify client is not initialized")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    async def search_spotify(self, query: str, limit: int = 10):
        try:
            # Ensure Spotify client is initialized
            if self.spotify is None:
                raise ValueError("Spotify client is not initialized")

            # Run the Spotify search function in an executor
            search_results = await self._run_spotify_func(self.spotify.search, query, type='track', limit=limit)
            
            # Extract relevant information from search results
            tracks = search_results['tracks']['items']
            results = []
            for track in tracks:
                track_info = {
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'url': track['external_urls']['spotify']
                }
                results.append(track_info)
            return results
        except Exception as e:
            print(f"Error searching Spotify: {e}")
            return []

    async def track(self, link: str):
        try:
            track = await self._run_spotify_func(self.spotify.track, link)
            info = track["name"]
            for artist in track["artists"]:
                fetched = f' {artist["name"]}'
                if "Various Artists" not in fetched:
                    info += fetched
            results = VideosSearch(info, limit=1)
            for result in (await results.next())["result"]:
                ytlink = result["link"]
                title = result["title"]
                vidid = result["id"]
                duration_min = result["duration"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            track_details = {
                "title": title,
                "link": ytlink,
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }
            return track_details, vidid
        except Exception as e:
            print(f"Error fetching track details: {e}")
            return None, None

    async def playlist(self, url):
        try:
            playlist = await self._run_spotify_func(self.spotify.playlist, url)
            playlist_id = playlist["id"]
            results = []
            for item in playlist["tracks"]["items"]:
                music_track = item["track"]
                info = music_track["name"]
                for artist in music_track["artists"]:
                    fetched = f' {artist["name"]}'
                    if "Various Artists" not in fetched:
                        info += fetched
                results.append(info)
            return results, playlist_id
        except Exception as e:
            print(f"Error fetching playlist details: {e}")
            return [], None

    async def album(self, url):
        try:
            album = await self._run_spotify_func(self.spotify.album, url)
            album_id = album["id"]
            results = []
            for item in album["tracks"]["items"]:
                info = item["name"]
                for artist in item["artists"]:
                    fetched = f' {artist["name"]}'
                    if "Various Artists" not in fetched:
                        info += fetched
                results.append(info)
            return results, album_id
        except Exception as e:
            print(f"Error fetching album details: {e}")
            return [], None

    async def artist(self, url):
        try:
            artistinfo = await self._run_spotify_func(self.spotify.artist, url)
            artist_id = artistinfo["id"]
            results = []
            artisttoptracks = await self._run_spotify_func(self.spotify.artist_top_tracks, url)
            for item in artisttoptracks["tracks"]:
                info = item["name"]
                for artist in item["artists"]:
                    fetched = f' {artist["name"]}'
                    if "Various Artists" not in fetched:
                        info += fetched
                results.append(info)
            return results, artist_id
        except Exception as e:
            print(f"Error fetching artist details: {e}")
            return [], None