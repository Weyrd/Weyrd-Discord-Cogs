from .gw2 import GuildWars2
import asyncio

def setup(bot):
    n = GuildWars2(bot)
    loop = asyncio.get_event_loop()
    loop.create_task(n._gamebuild_checker())
    bot.add_cog(n)
