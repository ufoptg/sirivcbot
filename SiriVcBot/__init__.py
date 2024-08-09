from SiriVcBot.core.bot import VasudevKrishna
from SiriVcBot.core.dir import dirr
from SiriVcBot.core.git import git
from SiriVcBot.core.userbot import Userbot
from SiriVcBot.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = VasudevKrishna()
userbot = Userbot()


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
#YouTube = YouTubeAPI()
