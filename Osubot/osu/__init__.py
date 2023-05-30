__title__ = "osuapi"
__author__ = "khazhyk modified and improved by Wyrd rëisa, discord implementation by Wyrd rëisa"
__license__ = "MIT"
__copyright__ = "Copyright khazhyk / Wyrd\'"
__versionapi__ = "1.0.33"
__versiondiscord__ = "2.1"

import os
from .osu import Osu
from .connectors import *
import json

if os.name == 'nt':
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("\\")[:-1]) +  "/data/osu/data.json"
else:
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1]) +  "/data/osu/data.json"

def setup(bot):
    """Start the cog and check API keys"""
    #check_folders()
    #check_files()
    with open(datapath) as openfile:
        data = json.load(openfile)
        keys = data.get("keys")
        if keys:
            key_osu = keys.get("osu")
            key_gyazo = keys.get("gyazo")
        else:
            key_gyazo = ""
            key_osu = ""
    bot.add_cog(Osu(bot, key_osu, key_gyazo, connector=ReqConnector()))
