from .listenerosu import Listenerosu
import asyncio
import os
import json

if os.name == 'nt':
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("\\")[:-1]) +  "/data/osu/data.json"
else:
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1]) +  "/data/osu/data.json"

def setup(bot):
    with open(datapath) as openfile:
        data = json.load(openfile)
        keys = data.get("keys")
        if keys:
            key_osu = keys.get("osu")
            key_gyazo = keys.get("gyazo")
        else:
            key_gyazo = ""
            key_osu = ""

    n = Listenerosu(bot, key_osu, key_gyazo)
    loop = asyncio.get_event_loop()
    bot.add_listener(n.emote, "on_message")
    bot.add_listener(n.beatmap, "on_reaction_add")
    bot.add_cog(Listenerosu(bot, key_osu, key_gyazo))
