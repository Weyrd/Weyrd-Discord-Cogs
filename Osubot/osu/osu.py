"""It's just... a implementation of Osu!api in discord ¯|_(ツ)_/¯"""

import json
import re
from time import strftime, gmtime
import os
import asyncio
import datetime
import discord
from redbot.core import commands
import random

import matplotlib.pyplot as plt
from matplotlib.patches import Arc
from gyazo import Api

import aiohttp
from aiohttp_requests import requests
from bs4 import BeautifulSoup
import matplotlib.animation as animation
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

from .model import  BeatmapScore, RecentScore, SoloScore, OsuMode, Beatmap, Game
from . import endpoints
from .connectors import ReqConnector


"""
try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Arc
    from gyazo import Api

except ImportError:
    with open("requierment.bat", "w") as bat:
        bat.write("@echo on\n"
                  "echo Install requierments"
                  "start /MIN python -m pip install -U setuptools pip\n"
                  "start /MIN python -m pip install matplotlib\n"
                  "start /MIN python -m pip install python-gyazo")
        bat.close()
        os.system("requierment.bat")
        asyncio.sleep(5)
        os.remove("requierment.bat")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Arc
        from gyazo import Api
"""

global datapath
global datapathimages
if os.name == 'nt':
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("\\")[:-1]) +  "/data/osu/"
    datapathimages = "/".join(os.path.dirname(os.path.abspath(__file__)).split("\\")[:-1]) +  "/data/osu/Images/"

else:
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1]) +  "/data/osu/"
    datapathimages = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1]) +  "/data/osu/Images/"

async def _get_page(url):
    r = await requests.get(url)
    page = await r.text()
    return page

async def _get_image(url):
    try:
        async with aiohttp.ClientSession().get(url) as f:
            data = await f.read()
        return Image.open(BytesIO(data)).convert("RGBA")
    except Exception:
        img = Image.new("RGBA",(250,250), (0,0,0,0))
        return img

def _add_corners(im, rad):
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2, rad * 2), fill=255)
    alpha = Image.new('L', im.size, 255)

    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im

def _size_text(im, text, proportion):
    font = ImageFont.load_default()
    fontsize = 1
    while font.getsize(text)[0] < proportion*im.size[0] and font.getsize(text)[1] < proportion*(im.size[1]*1.1):
        fontsize += 1
        font = ImageFont.truetype(datapath + "PLUMP.TTF", fontsize, encoding="unic")
    #print("{} : {}".format(text, fontsize))
    return font


def _username_type(username):
    """return type of username"""
    if username is None:
        return None
    return "id" if isinstance(username, int) else "string"

def _rank_spacing(rank):
    """Use to spaced str number greater than 1000"""
    # or use that on one line xD
    #str(" ".join(re.findall('.{1,3}',
                 #(floor(float(pp_raw)[::-1]))[::-1])) +
                 #(str((float(pp_raw)-int(float(pp_raw))))[1:])[:4]
    # just for eyes beacause is so beautiful
    rank = str(rank).split(".")
    rank_decimal = rank[-1]if len(rank) > 1 else ""
    rank = rank[0]

    if len(rank) > 3:
        list_number = re.findall('.{1,3}', rank[::-1])
        rank = (" ".join(list_number))[::-1]
        rank += ".{}".format("".join(rank_decimal))


    else:
        rank = "{}.{}".format(rank, rank_decimal)

    while rank[-1:] == "0":
        if len(rank.split(".")) > 1:
            rank = rank[:-1]


    while rank[-1:] == ".": # C'est brutal mais vire les .
        rank = rank[:-1]

    if rank == "":
        rank = "0"
    return rank

def _key_exist_osu():
    """Check osu key in data file"""
    with open(datapath + "data.json") as openfile:
        data = json.load(openfile)
        keys = data.get("keys")
        if keys:
            key_osu = keys.get("osu")
            if key_osu:
                return True

        return False

def __repr__(self, thing): # Alors Aza je sais pas si tu tomberas la dessus
    """Euh is a __repr__ function, I think :LUL:"""# un jours... Mais ne montre jamais ça
    tranplane = "{" + "0.{}".format(thing) + "}" #  a personne. Cette fonction est vraiment dégeulasse xDDD
    return tranplane.format(self) #genre le pire de tout je sais meme pas comment elle fonctionne. Mais ca marche xDD

def _date_formating(date):
    """Return Osu date in a pre-formatted format"""
    year = date[:4]
    jour = date[8:10]
    mois = date[5:7]
    heure = str(int(date[11:13]) + 1) # Décalage horaire
    if len(heure) == 1:
        heure = "0{}".format(heure) # Pour faire plus bo :o
    minute = date[14:16]
    seconde = date[17:19]
    date = "{}~{}~{} à {}H{}:{}s".format(jour, mois, year, heure, minute, seconde)
    return date

def _beatmap_name(name):
    name = re.sub("\((.*)\)", "", name) #<.*?>
    if len(name) > 25:
        name = re.sub("(\[.*\])", "", name) # :.*?: = tout entre :
        if len(name) > 25:
            name = re.sub("(~.*~)", "", name)
            if len(name) > 25:
                name = name[:20] + "..."
    return name

def _get_emote():
    path = datapath + "Images/emotes/"
    with open(datapath + "data.json") as openfile:
        emotes = json.load(openfile)
        emotes = emotes.get("emotes")

        emote_list = []
        for dirpath, dirnames, files in os.walk(path):
            for filename in files:
                filename = filename.split(".")[0]
                emote_list.append(filename)

        error = ""
        if emotes:
            del emotes["server_id"]
            for emote in emote_list:
                if not emote in emotes:
                    error = ("Toutes les emotes ne se sont pas créées correctement"
                             ". Merci de taper `[p]osuemote delete` suivi de "
                             "`[p]osuemote create`"
                             " dans le serveur de votre choix")
                    emotes[emote] = ""


        else:
            emotes = {}
            for emote in emote_list:
                emotes[emote] = ""

            error = ("N'oubliez pas que vous pouvez rajouter des"
                     " jolies emotes dans les messages en faisaint "
                     "`[p]osuemote create`"
                     " dans le serveur de votre choix")

        if not error:
            error = ""
        return emotes, error



class Osu(commands.Cog):
    """Class : Osu!Api"""
    def __init__(self, bot, key_osu, key_gyazo, *, connector):
        """AQUMAYAWINHKFAXAPERAOORUSQYVBCNLKOIFFMGRRP INIT"""
        self.bot = bot
        self.connector = connector
        self.key = key_osu
        self.gyazo_key = Api(access_token=key_gyazo)
        self.actual_file = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1])
        self.color = (194,194,194)
        self.color2 = (153,156,158)
        self.color_profile = (234,234,234)



    def close(self):
        """Hmm I love Pylint :O"""
        self.connector.close()

    def _make_req(self, endpoint, data):#, type_):
        """Make the Osu! API requests"""
        return self.connector.process_request(endpoint,
                                              {k: v for k, v in data.items() if v is not None})
                                              #, type_)

    def _upload_gyazo(self, path):
        """Upload image on gyazo and return link"""
        with open(path, 'rb') as file:
            error = "erreur non reconnu pdtr"
            url_pp = ""
            try:
                image = self.gyazo_key.upload_image(file)
                url_pp = json.loads(image.to_json()).get("url")
                error = ""
            except Exception as error:
                error = ("Merci de renseigner une clé API `gyazo` valide !\n"
                         "```{} : {}```".format(type(error).__name__, error))

                url_pp = ""
            return url_pp, error


    def _get_beatmapset_id(self, beatmap_id):
        """Get the beatmapset id and title by beatmap id"""
        get_map = (self._make_req(endpoints.BEATMAPS, dict(
            k=self.key,
            b=beatmap_id,
            limit=1
            )))#, JsonList(Beatmap)))

        beatmapset_id = get_map[0].get("beatmapset_id")
        title = _beatmap_name(get_map[0].get("title"))
        return beatmapset_id, title

    def _get_username(self, user_id):
        """Just get user name by user id"""
        user = (self._make_req(endpoints.USER, dict(
            k=self.key,
            u=user_id,
            type=_username_type(user_id),
            )))#, JsonList(User)))

        username = user[0].get("username")
        return username

    def _get_user_save(self, id):
        with open(datapath + "data.json") as j:
            usersave = json.load(j).get("users")
            if usersave:
                if str(id) in usersave:
                    username = usersave.get(str(id))
                else : username = ""
            else: username = ""
        return username


    def _get_graph(self, user_graph):

        plt.figure(facecolor='#2a2226', figsize=(13, 4))
        graph = plt.subplot()

        y = user_graph.get("data")
        x = []
        for i in range(len(y)):
            x.append(len(y)-i)

        plt.rcParams.update({'font.size': 22, 'ytick.major.size': 3.5})

        graph.plot(x, y, color='#ffcc22', linewidth=3)
        graph.invert_xaxis()
        graph.invert_yaxis()

        graph.set_ylim((max(y)+(max(y)*7)/100), (min(y)-(min(y)*7)/100))
        graph.set_xlim(90, 0)
        graph.set_frame_on(False)

        graph.tick_params(labelsize=15, width=2, colors='#ffffff')
        graph.grid(alpha=0.4, linestyle='--')


        locs, labels = plt.yticks()
        rank_list = []
        for rank in locs:
            if str(int(rank.item()))[-3:] == "000":
                rank = str(int(rank.item()))[:-3]+ " k"
                rank_list.append(rank)
            else:
                rank_list.append(str(rank)[:-2])


        ################## hmmmm
        try:
            locs = list(locs)
            del rank_list[-1]
            del locs[-1]
        except Exception:
            pass
        #################

        plt.yticks(locs, rank_list)

        plt.savefig(datapath + "temp/graph_done.png", transparent=True)
        #graph_done = BytesIO()
        #plt.savefig(graph_done, format='png')
        plt.close()
        #return graph_done

    def _get_plays(self, user_info):

        monthly_playcounts = user_info.get("monthly_playcounts") # {'start_date': '2017-10-01', 'count': 153}, {'start_date': '2017-11-01', 'count'..

        datetime = []
        play = []

        for month in monthly_playcounts:
            datetime.append(month.get("start_date"))
            play.append(month.get("count"))



        plt.figure(facecolor='#2a2226', figsize=(13, 4))
        playmonth = plt.subplot()

        playmonth.plot(datetime, play, color='#ffcc22', linewidth=3)

        playmonth.xaxis.set_major_locator(plt.MaxNLocator(7))
        playmonth.set_frame_on(False)

        plt.rcParams.update({'font.size': 22, 'ytick.major.size': 3.5})
        playmonth.tick_params(labelsize=15, width=2, colors='#ffffff')
        playmonth.grid(alpha=0.4, linestyle='--')

        plt.savefig(datapath + "temp/play_done.png", transparent=True)
        #play_done = BytesIO()
        #plt.savefig(play_done, format="png")
        #play_done.seek(0)
        plt.close()

    async def _get_cover_user(self, user_info, user):

        def emplacement_txt(im, text, font, x):
            return (int(im.size[0]-font.getsize(text)[0]-(im.size[0]*0.02)), x)

        avatar_url = user_info.get("avatar_url")
        cover_url = user_info.get("cover_url")

        loop = asyncio.get_event_loop()
        cover_user =  loop.create_task(_get_image(cover_url))
        avatar_user = loop.create_task(_get_image(avatar_url))

        cover_user = await cover_user
        avatar_user = await avatar_user


        enhancer = ImageEnhance.Brightness(cover_user)
        cover_user = enhancer.enhance(0.7)
        cover_user = cover_user.filter(ImageFilter.BLUR)

        avatar_user = _add_corners(avatar_user, 35)

        size = (int(int(cover_user.size[1])*0.602)), int(int(cover_user.size[1])*0.602)
        avatar_user = avatar_user.resize(size, Image.ANTIALIAS)

        #size = (cover_user.size[0], int(int(avatar_user.size[1])*1.660)) #adapter cover a la taille de la pp
        #cover_user = cover_user.resize(size, Image.ANTIALIAS)

        decalage = int((cover_user.size[1] - avatar_user.size[1])/2)
        cover_user.paste(avatar_user, (int(decalage/2), decalage), avatar_user)

        cover_user = _add_corners(cover_user, 20)
        draw_cover = ImageDraw.Draw(cover_user)


        user_id = user.get("user_id")
        username = user.get("username")
        join_date = _date_formating(user.get("join_date"))
        playcount = _rank_spacing((user.get("playcount")))
        country = user.get("country")
        total_seconds_played = user.get("total_seconds_played")

        pp_rank = _rank_spacing(user.get("pp_rank"))
        level = _rank_spacing(user.get("level"))
        pp_raw = _rank_spacing(user.get("pp_raw"))
        pp_country_rank = _rank_spacing(user.get("pp_country_rank"))

        time_play = strftime('%d jours, %HH %Mmn et %Ss', gmtime(int(total_seconds_played)))
        time_play = time_play.replace(str(time_play[0:2]), str(int(time_play[0:2])-1))

        pp = "Nombre pp : " + str(pp_raw)
        rank = "Rank : " + str(pp_rank)
        username = str(username)
        rank_pays = "Rank FR : " + str(pp_country_rank)
        ac = user_info.get("statistics").get("hit_accuracy")
        accuracy = "" + str(round(ac,2))
        tps_jeu = str(time_play)


        #Font
        font_pp = _size_text(cover_user, pp, 0.35)
        font_rank = _size_text(cover_user, pp, 0.35)
        font_pseudo = _size_text(cover_user, username, 0.34)
        font_rank_pays = _size_text(cover_user, rank_pays, 0.6)
        font_accuracy = _size_text(cover_user, accuracy, 0.09)
        font_temps = _size_text(cover_user, tps_jeu, 0.5)

        #emplacement
        y = cover_user.size[1]/5 + 5
        decalage_y = 29
        pp_emplacement = emplacement_txt(cover_user, pp, font_pp, decalage_y)
        rank_emplacement = emplacement_txt(cover_user, rank, font_rank, y+decalage_y)
        pseudo_emplacement = (int(cover_user.size[0]*0.19), int(cover_user.size[1]*0.04))
        rank_pays_emplacement = emplacement_txt(cover_user, rank_pays, font_accuracy, y*2+decalage_y+10)#va savoir mais ça marche.. (le font_accuracy)
        accuracy_emplacement = emplacement_txt(cover_user, accuracy, font_accuracy, y*3+decalage_y)
        tps_jeu_emplacement = emplacement_txt(cover_user, tps_jeu, font_temps,cover_user.size[1]-cover_user.size[1]*0.13)

        #text
        draw_cover.text(pp_emplacement, pp,  font=font_pp, fill=self.color_profile)#longeur, hauteur
        draw_cover.text(rank_emplacement, rank,  font=font_rank, fill=self.color_profile)
        draw_cover.text(pseudo_emplacement, username,  font=font_pseudo, fill=self.color_profile)
        draw_cover.text((rank_pays_emplacement), rank_pays, font=font_accuracy, fill=self.color_profile)
        draw_cover.text(accuracy_emplacement, accuracy, font=font_accuracy, fill=self.color_profile)
        draw_cover.text(tps_jeu_emplacement, tps_jeu, font=font_temps, fill=self.color_profile)#, 124))

        cover_user_save = BytesIO()
        cover_user.save(cover_user_save, format='PNG')
        cover_user.close()
        return cover_user_save

    def _get_fail(self, info_beatmap, n_beatmap):

        plt.figure(facecolor='#2a2226', figsize=(13, 4))
        fail = plt.subplot()

        x = [x for x in range(100)]
        y = info_beatmap.get("beatmaps")[n_beatmap].get("failtimes").get("fail")

        plt.rcParams.update({'font.size': 22, 'ytick.major.size': 3.5})

        fail.plot(x, y, color='#ffcc22', linewidth=3)


        fail.set_ylim(min(y), max(y))
        fail.set_xlim(0, 100)
        fail.set_frame_on(False)

        fail.tick_params(labelsize=15, width=2, colors='#ffffff')
        fail.grid(alpha=0.4, linestyle='--')

        locs, labels = plt.yticks()
        rank_list = []
        for rank in locs:
            if str(int(rank.item()))[-3:] == "000":
                rank = str(int(rank.item()))[:-3]+ " k"
                rank_list.append(rank)
        plt.yticks(locs, rank_list)

        plt.savefig(datapath + "temp/fail_done.png", transparent=True)
        #fail_done = BytesIO()
        #plt.savefig(fail_done, format='png')
        plt.close()


        fail_done = Image.open(datapath + "temp/fail_done.png").convert("RGBA")
        im_fail = Image.new('RGBA', (fail_done.size[0], int(fail_done.size[1]+fail_done.size[1]*0.1 + 50)), color="#222222")
        im_fail.paste(fail_done, (0, im_fail.size[1]-fail_done.size[1]))
        draw_fail = ImageDraw.Draw(im_fail)

        playcount_diff = info_beatmap.get("beatmaps")[n_beatmap].get("playcount")
        passcount = info_beatmap.get("beatmaps")[n_beatmap].get("passcount")
        taux_pass = "Sucess rate : " + str(round((passcount*100/playcount_diff), 2))

        font_taux_pass = _size_text(fail_done, taux_pass, 0.40)
        taux_pass_emplacement =  (int(im_fail.size[0]/2-font_taux_pass.getsize(taux_pass)[0]/2), 25)
        draw_fail.text(taux_pass_emplacement, taux_pass, font=font_taux_pass)

        im_fail_save = BytesIO()
        im_fail.save(im_fail_save, format='PNG')
        return im_fail_save

    async def _get_cover_map(self, info_beatmap):
        cover_beatmap = info_beatmap.get("covers").get("cover@2x")
        cover_beatmap =  await asyncio.get_event_loop().create_task(_get_image(cover_beatmap))

        enhancer = ImageEnhance.Brightness(cover_beatmap)
        cover_beatmap = enhancer.enhance(0.65)
        cover_beatmap = cover_beatmap.filter(ImageFilter.BLUR)
        cover_beatmap = _add_corners(cover_beatmap, 20)

        support = Image.open(datapathimages + "support.png").convert("RGBA")
        support = support.resize((int(cover_beatmap.size[0]*0.04), int(cover_beatmap.size[1]*0.1)))
        support = _add_corners(support, 15)
        playcount = Image.open(datapathimages + "playcount.png").convert("RGBA")
        playcount = playcount.resize((int(cover_beatmap.size[0]*0.04), int(cover_beatmap.size[1]*0.11)))

        draw_cover = ImageDraw.Draw(cover_beatmap)

        title = _beatmap_name(info_beatmap.get("title"))
        nom_diff = info_beatmap.get("artist")
        if len(nom_diff) > 15:
            nom_dif = nom_dif[:15]

        status = info_beatmap.get("status") #ranked...
        favourite_count = str(_rank_spacing(info_beatmap.get("favourite_count")))
        play_count_map = str(_rank_spacing(info_beatmap.get("play_count")))


        font_title = _size_text(cover_beatmap, title, len(title)*0.70/24)
        font_nom_diff = _size_text(cover_beatmap, nom_diff, 0.22)
        font_status = _size_text(cover_beatmap, status, 0.11)

        title_emplacement = (int(cover_beatmap.size[0]*0.05), int(cover_beatmap.size[1]*0.1))
        nom_diff_emplcement = (int(cover_beatmap.size[0]*0.12), int(cover_beatmap.size[1]*0.1 + font_title.getsize(title)[1] + 40))
        status_emplacement = (int(cover_beatmap.size[0]*0.12), int(cover_beatmap.size[1] - font_status.getsize(status)[1] -15))
        favourite_count_emplacement = (int(cover_beatmap.size[0]*0.70 + support.size[0] + 25), int(cover_beatmap.size[1] - font_status.getsize(status)[1] -15))
        play_count_map_emplacement = (int(cover_beatmap.size[0]*0.70 + support.size[0] + 25), int(cover_beatmap.size[1] - font_status.getsize(status)[1] - support.size[1] -15*2))

        draw_cover.text(title_emplacement, title,  font=font_title, fill=self.color_profile)#longeur, hauteur
        draw_cover.text(nom_diff_emplcement, nom_diff,  font=font_nom_diff, fill=self.color_profile)
        draw_cover.text(status_emplacement, status,  font=font_status, fill=self.color)
        draw_cover.text(favourite_count_emplacement, favourite_count,  font=font_status, fill=self.color_profile)
        draw_cover.text(play_count_map_emplacement, play_count_map,  font=font_status, fill=self.color_profile)

        cover_beatmap.paste(support, (int(cover_beatmap.size[0]*0.70), int(cover_beatmap.size[1] - font_status.getsize(status)[1] -20)))
        cover_beatmap.paste(playcount, (int(cover_beatmap.size[0]*0.70), int(cover_beatmap.size[1] - font_status.getsize(status)[1] - support.size[1] -20*2)))



        cover_beatmap_save = BytesIO()
        cover_beatmap.save(cover_beatmap_save, format='PNG')
        cover_beatmap.close()
        return cover_beatmap_save

    def _waiting(self):
        ooo = [
        "Oula, vous êtes un trop bon joueur, attendez un p'tit peu que je vois tout ça..",
        "Veuillez patienter...",
        "Alors, désolé, vous êtes vraiment nul, va falloir attendre un peu que je trouve un truc à afficher..",
        "Préparation en cours...",
        "J'ai bien vu votre commande, mais j'ai un peu la flemme de le faire, ça va prendre un peu de temps..",
        "Hei, vent, dette er et rot !",
        "Niktamayr ça arrive D:",
        "||:loading:||",
        "Pour passer le temps en attendant : ||perdu||, ||gagné||",
        "Pour passer le temps en attendant : ||gagné||, ||perdu||",
        "J'ai plus d'inspi donc t'attend comme tout le monde D:"
        ]
        ooo.append("Si vous voulez vos info, votre temps d'attente est estimé à {}s".format(random.randint(24,148)))
        return ooo[random.randint(0,len(ooo)-1)]






# COMMANDS GROUPS USER

    @commands.group(name="user", aliases=["u"])
    async def _user(self, ctx):
        """All user's actions possible in Osu!API"""
        #await self.bot.delete_message(ctx.message)
        if ctx.invoked_subcommand is None:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_star = emotes.get("OStar")

            user_help = discord.Embed(title="Contact me" + emote_star,
                                      url="https://discordapp.com/"
                                          "channels/@me/281798798727184384",
                                      description="To use that commands,"
                                                  " write `[p]user <commands>`",
                                      color=0x8080ff)
            user_help.set_author(name="Possibles user's group commands")
                                 #, url="")
            #user_help.set_thumbnail(url="")

            user_help.add_field(name="user profile :",
                                value="Retrieve general user information" + emote_supporter,
                                inline=False)
            user_help.add_field(name="user best :",
                                value="Get the top scores for the specified user",
                                inline=True)
            user_help.add_field(name="user recent :",
                                value="Gets the user's ten most recent plays over"
                                      " the last 24 hours.",
                                inline=True)
            user_help.set_footer(text="/o/")
            await ctx.send(embed=user_help)


    @_user.command(aliases=["p"])
    async def profile(self, ctx, username=None, mode="osu", event_days=31):
        """<username> [mode] [events]

        Parameters :
        ----------
            username=None : str or int
                username or id_user

            mode : str (optional)
                osu / taiko / ctb / mania. Default to osu

            envents : int (optional)
                x lasts days events. Default to 5 max 31
            """
        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        if not username:
            username = self._get_user_save(ctx.author.id)

        user = (self._make_req(endpoints.USER, dict(
            k=self.key,
            u=username,
            type=_username_type(username),
            m=mode.value,
            event_days=event_days
            )))#, JsonList(User)))

        if not user:
            if username:
                await ctx.send("Le joueur **{}** n'existe pas !".format(username))
            else: await ctx.send('Tapez `[p]save <pseudo_osu>`pour vous enregistrer !')
        else:
            messaenattente = await ctx.send(self._waiting())
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_medal = emotes.get("OsuMedal")
            emote_rank = emotes.get("OsuRank")

            user = user[0]
            user_id = user.get("user_id")
            level = user.get("level")
            pp_raw = user.get("pp_raw")
            join_date = _date_formating(user.get("join_date"))


            # create im_profile
            loop = asyncio.get_event_loop()
            page = loop.create_task(_get_page('https://osu.ppy.sh/users/{}'.format(user_id)))
            page = await page


            soup = BeautifulSoup(page, 'html.parser')# rankHistory

            user_graph = json.loads(soup.find(id="json-user").string.replace(' ', ''))["rankHistory"]
            user_info = json.loads((soup.find(id="json-user").string).replace(' ', ''))

            cover_user = Image.open(await self._get_cover_user(user_info, user)).convert("RGBA")

            self._get_graph(user_graph)
            self._get_plays(user_info)

            graph_done = Image.open(datapath + "temp/graph_done.png").convert("RGBA")
            play_done = Image.open(datapath + "temp/play_done.png").convert("RGBA")

            zoom_y = int(cover_user.size[1]*0.2)# pour pas trop déformer les graphs
            decalage_text = int(cover_user.size[1]*0.2)

            graph_done = graph_done.resize((cover_user.size[0], cover_user.size[1]+zoom_y), Image.ANTIALIAS)
            play_done = play_done.resize((cover_user.size[0], cover_user.size[1]+zoom_y), Image.ANTIALIAS)


            im_profile = Image.new('RGBA', (cover_user.size[0], cover_user.size[1]*3 + zoom_y*2 + decalage_text*2))

            im_profile.paste(cover_user, (0, 0))
            im_profile.paste(graph_done, (0, cover_user.size[1] + decalage_text))
            im_profile.paste(play_done, (0, cover_user.size[1]*2 + zoom_y + decalage_text*2))

            draw_profile = ImageDraw.Draw(im_profile)

            profile_rank = "Global ranking"
            profile_play = "Plays history"

            font_profile_rank = _size_text(im_profile, profile_rank, 0.40)
            font_profile_plays = _size_text(im_profile, profile_play, 0.40)

            profile_rank_emplacement = (int(cover_user.size[0]/2-font_profile_rank.getsize(profile_rank)[0]/2), int(cover_user.size[1] + decalage_text/2))
            profile_play_emplacement = (int(cover_user.size[0]/2-font_profile_plays.getsize(profile_play)[0]/2), int(cover_user.size[1]*2 + decalage_text*2.5))

            draw_profile.text(profile_rank_emplacement, profile_rank, font=font_profile_rank, fill=self.color)
            draw_profile.text(profile_play_emplacement, profile_play, font=font_profile_plays, fill=self.color)


            #im_profile_save = BytesIO()
            #im_profile.save(im_profile_save, format='PNG')
            im_profile.save(datapath + "temp/cover_user.png", format='PNG')



            path = datapath + "temp/pp_temp.png"
            level = str(round(float(level), 2)) # arrondi 2 décimals
            pp_raw = str(round(float(pp_raw), 2))

            cercle = float(int(level.split(".")[-1])*360/100)
            plt.figure(figsize=(10, 10))
            axe = plt.subplot()
            axe.invert_xaxis()

            axe.add_patch(Arc((10, 10), 19, 19, -270, linewidth=48, color='dimgrey'))
            axe.add_patch(Arc((10, 10), 19, 19, -270, theta2=cercle, linewidth=48,
                              color='dodgerblue'))
            axe.text(10, 13, r'Level', fontsize=79, color='lawngreen',
                     horizontalalignment='center', #fontfamily='fantasy',
                     fontweight='heavy', verticalalignment='center')
            axe.text(10, 8, level, fontsize=109, color='lawngreen',
                     horizontalalignment='center', #fontfamily='serif',
                     fontweight='heavy', verticalalignment='center')


            axe.plot(10, 10)
            plt.axis('off')
            plt.savefig(path, transparent=True)
            plt.cla()

            url_cover, error = self._upload_gyazo(datapath + "temp/cover_user.png")
            if error:
                await ctx.send(error)
            os.remove(datapath + "/temp/cover_user.png")
            os.remove(datapath + "/temp/graph_done.png")
            os.remove(datapath + "/temp/play_done.png")


            url_pp, error = self._upload_gyazo(path)
            if error:
                await ctx.send(error)
            os.remove(path)



            #DEF EMBED
            user_embed = discord.Embed(title="Voir le profil",
                                       url="https://osu.ppy.sh/users/" + user_id,
                                       color=0x008000)
            user_embed.set_author(
                name="{}'s profile (ID={})".format(username, user_id))
                                  #    ,icon_url=level)
            user_embed.set_thumbnail(url=url_pp)


            user_embed.set_image(url=url_cover)
            user_embed.set_footer(text=" A rejoins Osu! le : {}"
                                       "".format(join_date))

            await messaenattente.delete()
            await ctx.send(embed=user_embed)


    @_user.command(aliases=["s"])
    async def stats(self, ctx, username=None, mode="osu", event_days=31):
        """<username> [mode] [events]

        Parameters :
        ----------
            username=None : str or int
                username or id_user

            mode : str (optional)
                osu / taiko / ctb / mania. Default to osu

            envents : int (optional)
                x lasts days events. Default to 5 max 31
            """

        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        if not username:
            username = self._get_user_save(ctx.author.id)

        user = (self._make_req(endpoints.USER, dict(
            k=self.key,
            u=username,
            type=_username_type(username),
            m=mode.value,
            event_days=event_days
            )))#, JsonList(User)))

        if not user:
            if username:
                await ctx.send("Le joueur **{}** n'existe pas !".format(username))
            else: await ctx.send('Tapez `[p]save <pseudo_osu>`pour vous enregistrer !')
        else:
            messaenattente = await ctx.send(self._waiting())
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_medal = emotes.get("OsuMedal")
            emote_rank = emotes.get("OsuRank")

            user = user[0]
            user_id = user.get("user_id")


            # create im_profile
            loop = asyncio.get_event_loop()
            page = loop.create_task(_get_page('https://osu.ppy.sh/users/{}'.format(user_id)))
            page = await page


            soup = BeautifulSoup(page, 'html.parser')
            user_graph = json.loads(soup.find(id="json-user").string.replace(' ', ''))["rankHistory"]
            user_info = json.loads((soup.find(id="json-user").string).replace(' ', ''))

            a = Image.open(datapath + "Images/a.png").convert("RGBA")
            s = Image.open(datapath + "Images/s.png").convert("RGBA")
            s_silver = Image.open(datapath + "Images/s_silver.png").convert("RGBA")
            ss = Image.open(datapath + "Images/ss.png").convert("RGBA")
            ss_silver = Image.open(datapath + "Images/ss_silver.png").convert("RGBA")

            cover_user = Image.open(await self._get_cover_user(user_info, user)).convert("RGBA")
            decalage = 25
            decalage_y = 32
            decalage_catego = 40
            dimension_rank = (int(cover_user.size[0]*0.1), int((cover_user.size[0]*0.1)/2))
            dimension = (cover_user.size[0], cover_user.size[1]*4 + decalage_catego + decalage*3)
            other_catego = cover_user.size[1] + dimension_rank[1]*5.5 + decalage*6 + decalage_catego*2


            a = a.resize(dimension_rank, Image.ANTIALIAS)
            s = s.resize(dimension_rank, Image.ANTIALIAS)
            s_silver = s_silver.resize(dimension_rank, Image.ANTIALIAS)
            ss = ss.resize(dimension_rank, Image.ANTIALIAS)
            ss_silver = ss_silver.resize(dimension_rank, Image.ANTIALIAS)



            im_stats = Image.new('RGBA', dimension, color="#2a2226")
            im_stats.paste(cover_user, (0, 0))
            im_stats.paste(ss_silver, (0, cover_user.size[1] + decalage + decalage_catego))
            im_stats.paste(ss, (0, cover_user.size[1] + dimension_rank[1] + decalage*2 + decalage_catego))
            im_stats.paste(s_silver, (0, cover_user.size[1] + dimension_rank[1]*2 + decalage*3 + decalage_catego))
            im_stats.paste(s, (0, cover_user.size[1] + dimension_rank[1]*3 + decalage*4 + decalage_catego))
            im_stats.paste(a, (0, cover_user.size[1] + dimension_rank[1]*4 + decalage*5 + decalage_catego))



            draw_cover = ImageDraw.Draw(im_stats)
            statistics = user_info.get("statistics")

            try:
                playstyle = ", ".join(user_info.get("playstyle"))
            except:
                playstyle =  "..."
            follower_count = "Amis : " + str(_rank_spacing(user_info.get("follower_count")))
            maximum_combo = "Combo max : " + str(_rank_spacing(statistics.get("maximum_combo")))
            total_hits = "Total hits : " + str(_rank_spacing(statistics.get("total_hits")))

            if user_info.get("is_supporter") == True: supporter = "Supporter : Uiii"
            else: supporter = "Supporter : Naah"

            play_time = statistics.get("play_time")#en s
            play_count =  "plays : " + str(_rank_spacing(statistics.get("play_count")))
            ranked_score =  "Score : " + str(_rank_spacing(statistics.get("ranked_score")))

            clique_minute = "Cliques par minute : {}".format(_rank_spacing(round(statistics.get("total_hits")/(play_time/60), 2)))
            clique_partie = "Cliques par map : {}".format(_rank_spacing(round(statistics.get("total_hits")/statistics.get("play_count"), 2)))


            count_rank_ss = _rank_spacing(user.get("count_rank_ss"))
            count_rank_ssh = _rank_spacing(user.get("count_rank_ssh"))
            count_rank_s = _rank_spacing(user.get("count_rank_s"))
            count_rank_sh = _rank_spacing(user.get("count_rank_sh"))
            count_rank_a = _rank_spacing(user.get("count_rank_a"))

            ss_silver_n = str(count_rank_ssh)
            ss_n = str(count_rank_ss)
            s_silver_n = str(count_rank_sh)
            s_n = str(count_rank_s)
            a_n = str(count_rank_a)

            """
            font_playstyle = _size_text(im_stats, playstyle, 0.40)
            font_follower_count = _size_text(im_stats, follower_count, 0.30)
            font_maximum_combo = _size_text(im_stats, maximum_combo, 0.20)
            font_total_hits = _size_text(im_stats, total_hits, 0.20)
            font_clique_minute = _size_text(im_stats, clique_minute, 0.10)"""
            font_a = _size_text(a, a_n, 0.77)

            def emplacement_txt(im, text, font, x):
                return (int(im.size[0]-font.getsize(text)[0]-(im.size[0]*0.02)), x)

            follower_count_emplacement = emplacement_txt(im_stats, follower_count, font_a, cover_user.size[1] + dimension_rank[1]*1.27 + decalage*2 + decalage_catego)
            maximum_combo_emplacement = emplacement_txt(im_stats, maximum_combo, font_a, cover_user.size[1] + dimension_rank[1]*2.27 + decalage*3 + decalage_catego)
            play_count_emplacement = emplacement_txt(im_stats, play_count, font_a, cover_user.size[1] + dimension_rank[1]*3.27 + decalage*4 + decalage_catego)
            supporter_emplacement = emplacement_txt(im_stats, supporter, font_a, cover_user.size[1] + dimension_rank[1]*4.27 + decalage*5 + decalage_catego)

            playstyle_emplacement = (int((im_stats.size[0]/2)-(font_a.getsize(playstyle)[0]/2)), other_catego)
            space = font_a.getsize(a_n)[1]
            total_hits_emplacement = (0, other_catego + space + decalage*2)
            clique_minute_emplacement = (0, other_catego + space*2 + decalage*4)
            clique_partie_emplacement = (0, other_catego + space*3 + decalage*6)
            ranked_score_emplacement = (int((im_stats.size[0]/2)-(font_a.getsize(ranked_score)[0]/2)), other_catego + decalage*15 + space*2)

            ss_silver_emplacement = (dimension_rank[0] + decalage_y, cover_user.size[1] + dimension_rank[1]*0.27 + decalage + decalage_catego)
            ss_emplacement = (dimension_rank[0] + decalage_y, cover_user.size[1] + dimension_rank[1]*1.27 + decalage*2 + decalage_catego)
            s_silver_emplacement = (dimension_rank[0] + decalage_y, cover_user.size[1] + dimension_rank[1]*2.27 + decalage*3 + decalage_catego)
            s_emplacement = (dimension_rank[0] + decalage_y, cover_user.size[1] + dimension_rank[1]*3.27 + decalage*4 + decalage_catego)
            a_emplacement = (dimension_rank[0] + decalage_y, cover_user.size[1] + dimension_rank[1]*4.27 + decalage*5 + decalage_catego)

            draw_cover.text(follower_count_emplacement, follower_count, font=font_a, fill=self.color)
            draw_cover.text(maximum_combo_emplacement, maximum_combo, font=font_a, fill=self.color)
            draw_cover.text(play_count_emplacement, play_count, font=font_a, fill=self.color)
            draw_cover.text(supporter_emplacement, supporter, font=font_a, fill=self.color)

            draw_cover.text(playstyle_emplacement, playstyle, font=font_a, fill=self.color2)
            draw_cover.text(total_hits_emplacement, total_hits, font=font_a, fill=self.color2)
            draw_cover.text(clique_minute_emplacement, clique_minute, font=font_a, fill=self.color2)
            draw_cover.text(clique_partie_emplacement, clique_partie, font=font_a, fill=self.color2)
            draw_cover.text(ranked_score_emplacement, ranked_score, font=font_a, fill=self.color2)

            draw_cover.text(a_emplacement, a_n, font=font_a, fill=self.color)
            draw_cover.text(s_emplacement, s_n, font=font_a, fill=self.color)
            draw_cover.text(s_silver_emplacement, s_silver_n, font=font_a, fill=self.color)
            draw_cover.text(ss_emplacement, ss_n, font=font_a, fill=self.color)
            draw_cover.text(ss_silver_emplacement,ss_silver_n, font=font_a, fill=self.color)



            #im_stats.show()
            #im_stats_save = BytesIO()
            #im_stats.save(im_stats_save, format='PNG')
            im_stats.save(datapath + "temp/cover_user.png", format='PNG')

            level = user.get("level")
            pp_raw = user.get("pp_raw")
            join_date = _date_formating(user.get("join_date"))



            path = datapath + "temp/pp_temp.png"
            level = str(round(float(level), 2)) # arrondi 2 décimals
            pp_raw = str(round(float(pp_raw), 2))

            cercle = float(int(level.split(".")[-1])*360/100)
            plt.figure(figsize=(10, 10))
            axe = plt.subplot()
            axe.invert_xaxis()

            axe.add_patch(Arc((10, 10), 19, 19, -270, linewidth=48, color='dimgrey'))
            axe.add_patch(Arc((10, 10), 19, 19, -270, theta2=cercle, linewidth=48,
                              color='dodgerblue'))
            axe.text(10, 13, r'Level', fontsize=79, color='lawngreen',
                     horizontalalignment='center', #fontfamily='fantasy',
                     fontweight='heavy', verticalalignment='center')
            axe.text(10, 8, level, fontsize=109, color='lawngreen',
                     horizontalalignment='center', #fontfamily='serif',
                     fontweight='heavy', verticalalignment='center')


            axe.plot(10, 10)
            plt.axis('off')
            plt.savefig(path, transparent=True)
            plt.cla()

            url_cover, error = self._upload_gyazo(datapath + "/temp/cover_user.png")
            if error:
                await ctx.send(error)
            os.remove(datapath + "/temp/cover_user.png")

            url_pp, error = self._upload_gyazo(path)
            if error:
                await ctx.send(error)
            os.remove(path)



            #DEF EMBED
            user_embed = discord.Embed(title="Voir le profil",
                                       url="https://osu.ppy.sh/users/" + user_id,
                                       color=0x008000)
            user_embed.set_author(
                name="{}'s profile (ID={})".format(username, user_id))
                                  #    ,icon_url=level)
            user_embed.set_thumbnail(url=url_pp)
            user_embed.set_image(url=url_cover)



            user_embed.set_footer(text=" A rejoins Osu! le : {}"
                                       "".format(join_date))

            await messaenattente.delete()
            await ctx.send(embed=user_embed)


    @_user.command(hidden=True)
    async def stonks(self, ctx, username=None, mode="osu"):
        """<username> [mode] [events]

        Parameters :
        ----------
            username=None : str or int
                username or id_user

            mode : str (optional)
                osu / taiko / ctb / mania. Default to osu

            envents : int (optional)
                x lasts days events. Default to 5 max 31
            """
        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        if not username:
            username = self._get_user_save(ctx.author.id)

        user = (self._make_req(endpoints.USER, dict(
            k=self.key,
            u=username,
            type=_username_type(username),
            m=mode.value,
            )))#, JsonList(User)))

        if not user:
            if username:
                await ctx.send("Le joueur **{}** n'existe pas !".format(username))
            else: await ctx.send('Tapez `[p]save <pseudo_osu>`pour vous enregistrer !')
        else:
            messaenattente = await ctx.send(self._waiting())
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_medal = emotes.get("OsuMedal")
            emote_rank = emotes.get("OsuRank")

            user = user[0]
            user_id = user.get("user_id")
            level = user.get("level")


            # create im_profile
            loop = asyncio.get_event_loop()
            page = loop.create_task(_get_page('https://osu.ppy.sh/users/{}'.format(user_id)))
            page = await page


            soup = BeautifulSoup(page, 'html.parser')
            user_graph = json.loads(soup.find(id="json-user").string.replace(' ', ''))["rankHistory"]
            user_info = json.loads((soup.find(id="json-user").string).replace(' ', ''))

            self._get_graph(user_graph)
            self._get_plays(user_info)
            graph_done = Image.open(datapath + "temp/graph_done.png").convert("RGBA")
            play_done = Image.open(datapath + "temp/play_done.png").convert("RGBA")
            stonks = Image.open(datapath + "Images/stonks.png")


            decalage_text = int(graph_done.size[1]*0.2)
            dimension = (graph_done.size[0], graph_done.size[1] + play_done.size[1] + decalage_text)
            stonks = stonks.resize(dimension, Image.ANTIALIAS)

            dimension_stonks = (0, dimension[1]-stonks.size[1])
            im_stonks = Image.new('RGBA', dimension)

            im_stonks.paste(play_done, (0, int(decalage_text/2)))
            im_stonks.paste(stonks, dimension_stonks)
            im_stonks.paste(graph_done, (0, play_done.size[1] + decalage_text))


            draw_stonks = ImageDraw.Draw(im_stonks)

            stonks_rank = "Global ranking"
            stonks_play = "Plays history"

            font_stonks_rank = _size_text(im_stonks, stonks_rank, 0.40)
            font_stonks_plays = _size_text(im_stonks, stonks_play, 0.40)

            stonks_play_emplacement = (int(graph_done.size[0]/2-font_stonks_rank.getsize(stonks_rank)[0]/2), 0)
            stonks_rank_emplacement = (int(graph_done.size[0]/2-font_stonks_plays.getsize(stonks_play)[0]/2), int(graph_done.size[1] + decalage_text))

            draw_stonks.text(stonks_rank_emplacement, stonks_rank, font=font_stonks_rank)
            #draw_stonks.text(stonks_play_emplacement, stonks_play, font=font_stonks_plays)

            #im_stonks.show()
            #im_stonks_save = BytesIO()
            #im_stonks.save(im_stonks_save, format='PNG')
            join_date = _date_formating(user.get("join_date"))

            im_stonks.save(datapath + "temp/stonks_user.png", format='PNG')

            url_stonks, error = self._upload_gyazo(datapath + "/temp/stonks_user.png")
            if error:
                await ctx.send(error)
            os.remove(datapath + "/temp/stonks_user.png")
            os.remove(datapath + "/temp/graph_done.png")
            os.remove(datapath + "/temp/play_done.png")

            #DEF EMBED
            user_embed = discord.Embed(title="Voir le profil",
                                       url="https://osu.ppy.sh/users/" + user_id,
                                       color=0x008000)
            user_embed.set_author(
                name="{}'s profile (ID={})".format(username, user_id))
                                  #    ,icon_url=level)
            user_embed.set_image(url=url_stonks)



            user_embed.set_footer(text=" A rejoins Osu! le : {}"
                                       "".format(join_date))

            await messaenattente.delete()
            await ctx.send(embed=user_embed)


    @_user.command(aliases=["b"])
    async def best(self, ctx, username=None, limit=3, mode="osu"):
        """<username> [limit=6] [mode]

        Parameters :
        ----------
            username : str or int
                username or id_user

            limit : int (optional)
                x first bests map. Defaults to 3 max 100

            mode : str (optional)
                osu / taiko / ctb / mania. Default to osu
            """
        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        if not username:
            username = self._get_user_save(ctx.author.id)

        maps = (self._make_req(endpoints.USER_BEST, dict(
            k=self.key,
            u=username,
            type=_username_type(username),
            m=mode.value,
            limit=limit
            )))#, JsonList(SoloScore)))


        if not maps:
            if username:
                await ctx.send("Le joueur **{}** n'existe pas "
                               "ou n'a jamais fini de map !".format(username))
            else: await ctx.send('Tapez `[p]save <pseudo_osu>`pour vous enregistrer !')
        else:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_rank = emotes.get("OsuRank")
            emote_star = emotes.get("OStar")

            user_id = maps[0].get('user_id')
            embed_map = discord.Embed(title="Voir le profil",
                                      url="https://osu.ppy.sh/users/" + user_id,
                                      color=0xba0388)

            embed_map.set_author(name="{}'s best play (ID={})"
                                      "".format(username.capitalize(), user_id))
                                 #,icon_url=None)

            #embed_map.set_thumbnail(url=None)


            for beatmap in maps:
                beatmap_id = beatmap.get('beatmap_id')
                beatmapset_id, beatmap_name = self._get_beatmapset_id(beatmap_id)


                point_player = str(round(float(beatmap.get('pp')), 2))
                rank = beatmap.get('rank')
                score = beatmap.get('score')
                #date = map.get('date') # _date_formating()

                enabled_mods = __repr__(SoloScore(beatmap), 'enabled_mods')

                if int(limit) < 7:
                    maxcombo = beatmap.get('maxcombo')
                    count50 = beatmap.get('count50')
                    count100 = beatmap.get('count100')
                    count300 = beatmap.get('count300')
                    countmiss = beatmap.get('countmiss')
                    countkatu = beatmap.get('countkatu')
                    countgeki = beatmap.get('countgeki')
                    perfect = beatmap.get('perfect')
                    score_stat = ("**Stat :**" + emote_rank +
                                  "\nCombo max : **{}**\nNombre de"
                                  " 50 : {}\nNombre de 100 : {}\n"
                                  "Nombre de 300 : **{}**\nNombre de Miss :"
                                  " **{}**\nNombre de katu : {}\n"
                                  "Nombre de geki : {}\nPerfect : {}\n\n"
                                  "".format(maxcombo, count50, count100,
                                            count300, countmiss, countkatu,
                                            countgeki, "Oui" if perfect == 1 else "Non"))
                else:
                    score_stat = None


                osu_direct_link = "<osu://dl/{}>".format(beatmapset_id)
                osu_link = "https://osu.ppy.sh/beatmapsets/" + beatmapset_id

                embed_map.add_field(name="{}".format(beatmap_name),
                                    value="{}"
                                          "\n**Infos :** [Lien Osu!]({})\n"
                                          "Nombre de pp : **{}**\n"
                                          "Rank : **{}** {}\n"
                                          "Score : {}\n"
                                          "Mods : {}\n\n"
                                          "{}"
                                          "".format(osu_direct_link,
                                                    osu_link,
                                                    _rank_spacing(point_player),
                                                    rank,
                                                    emote_star,
                                                    _rank_spacing(score),
                                                    enabled_mods,
                                                    score_stat if score_stat else ""
                                                    ), inline=True) #date


            await ctx.send(embed=embed_map)


    @_user.command(aliases=["r"])
    async def recent(self, ctx, username=None, limit=3, mode="osu"):#:int=OsuMode.osu):
        """<username> [mode] [events]

        Parameters :
        ----------
            username : str or int
                username or id_user

            limit : int (optional)
                x first bests map. Defaults to 3 max 100

            mode : int (optional)
             0 = osu / 1 = taiko / 2 = ctb / 3 = mania. Default to osu
            """
        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        #mode = OsuMode(mode)
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        if not username:
            username = self._get_user_save(ctx.author.id)

        maps = (self._make_req(endpoints.USER_RECENT, dict(
            k=self.key,
            u=username,
            type=_username_type(username),
            m=mode.value,
            limit=limit
            )))#, JsonList(RecentScore)))

        if not maps:
           if username:
               await ctx.send('Le joueur `{}` n\'existe pas ou n\'a pas fini '
                                  'de map en mode `{}` ces dernières 24h'
                                  ''.format(username, mode))
           else: await ctx.send('Tapez `[p]save <pseudo_osu>`pour vous enregistrer !')
        else:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_rank = emotes.get("OsuRank")
            emote_star = emotes.get("OStar")


            user_id = maps[0].get('user_id')
            embed_map = discord.Embed(title="Voir le profil",
                                      url="https://osu.ppy.sh/users/" + user_id,
                                      color=0xba0388)

            embed_map.set_author(name="{}'s recent play (ID={})"
                                      "".format(username.capitalize(), user_id))
                                 #,icon_url=None)

            #embed_map.set_thumbnail(url=None)

            for score_map in maps:
                beatmap_id = score_map.get('beatmap_id')

                pp_map = (self._make_req(endpoints.SCORES, dict( # try to get pp score of map
                    k=self.key,
                    b=beatmap_id,
                    u=username,
                    type=_username_type(username),
                    limit=limit)))#, JsonList(BeatmapScore)))

                beatmapset_id, beatmap_name = self._get_beatmapset_id(beatmap_id)

                if pp_map:
                    pp_map = pp_map[0]
                    point_player = _rank_spacing(str(round(float(pp_map.get('pp')), 2)))
                else: point_player = "`Uuh >~<`"
                rank = score_map.get('rank')
                score = score_map.get('score')
                #date = score_map.get('date') # _date_formating()

                enabled_mods = __repr__(RecentScore(score_map), 'enabled_mods')

                if int(limit) < 7:
                    maxcombo = score_map.get('maxcombo')
                    count50 = score_map.get('count50')
                    count100 = score_map.get('count100')
                    count300 = score_map.get('count300')
                    countmiss = score_map.get('countmiss')
                    countkatu = score_map.get('countkatu')
                    countgeki = score_map.get('countgeki')
                    perfect = score_map.get('perfect')
                    score_stat = ("**Stat :**" + emote_rank +
                                  "\nCombo max : **{}**\nNombre de 50 "
                                  ": {}\nNombre de 100 : {}\n"
                                  "Nombre de 300 : **{}**\nNombre de Miss : **{}**\n"
                                  "Nombre de katu : {}\n"
                                  "Nombre de geki : {}\nPerfect : {}\n\n"
                                  "".format(maxcombo, count50, count100,
                                            count300, countmiss, countkatu,
                                            countgeki, "Oui" if perfect == 1 else "Non"))
                else:
                    score_stat = None


                osu_direct_link = "<osu://dl/{}>".format(beatmapset_id)
                osu_link = "https://osu.ppy.sh/beatmapsets/" + beatmapset_id

                embed_map.add_field(name="{}".format(beatmap_name),
                                    value="{}"
                                          "\n**Infos :** [Lien Osu!]({})\n\n"
                                          "Nombre de pp : **{}**\n"
                                          "Rank : **{}** {}\n"
                                          "Score : {}\n"
                                          "Mods : {}\n\n"
                                          "{}"
                                          "".format(osu_direct_link,
                                                    osu_link,
                                                    point_player,
                                                    rank,
                                                    emote_star,
                                                    _rank_spacing(score),
                                                    enabled_mods,
                                                    score_stat if score_stat else "",
                                                    ),
                                    inline=True)


            await ctx.send(embed=embed_map)



# COMMANDS GROUPS GET

    @commands.group(name="get")
    async def _get(self, ctx):
        """All get's actions possible in Osu!API"""
        #await self.bot.delete_message(ctx.message)
        if ctx.invoked_subcommand is None:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_rank = emotes.get("OsuRank")
            emote_star = emotes.get("OStar")

            get_help = discord.Embed(title="Contact me" + emote_star,
                                     url="https://discordapp.com/channels/@me/281798798727184384",
                                     description="To use that commands, write `[p]get <commands>`",
                                     color=0x8080ff)
            get_help.set_author(name="Possibles get's group commands")
                                 #, url="")
            #user_help.set_thumbnail(url="")

            get_help.add_field(name="get score :" + emote_rank,
                               value="Retrieve information about the"
                                     " top x scores of a specified beatmap",
                               inline=True)
            get_help.add_field(name="get beatmap :",
                               value="Retrieve general beatmap information",
                               inline=False)
            get_help.add_field(name="get match :",
                               value="Retrieve information about multiplayer match",
                               inline=True)
            get_help.add_field(name="get replay :",
                               value="Not implemented.",
                               inline=True)
            get_help.set_footer(text="/o/")
            await ctx.send(embed=get_help)

    @_get.command()
    async def score(self, ctx, beatmap_id, username=None, limit=2, mode="osu", mods=None):
        """<beatmap_id> [username] [limit] [mode] [events]

        Parameters :
        ----------
            beatmap_id : int
                id of beatmap
            username : str or int (optional)
                username or id_user. Default first players World
            limit : int
                limit to get x best first score. Default 2
            mode : str (optional)
                osu / taiko / ctb / mania. Default to osu
            mod : :class:`osuap:class:`osuapi.enums.OsuMod`
                Not work for the time being lul
            """
        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        scores = (self._make_req(endpoints.SCORES, dict(
            k=self.key,
            b=beatmap_id,
            u=username,
            type=_username_type(username),
            m=mode.value,
            mods=mods.value if mods else None,
            limit=limit)))#, JsonList(BeatmapScore)))


        if not scores:
            if username:
                await ctx.send('La map `{}` n\'existe pas ou le joueur `{}` '
                                   'n\'a pas fini la map en `{}`'.format(beatmap_id,
                                                                         username, mode))
            else:
                await ctx.send('La map `{}` n\'existe pas'.format(beatmap_id))
        else:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_rank = emotes.get("OsuRank")
            emote_star = emotes.get("OStar")

            beatmapset_id, beatmap_name = self._get_beatmapset_id(beatmap_id)

            osu_direct_link = "<osu://dl/{}>".format(beatmapset_id)
            osu_link = "https://osu.ppy.sh/beatmapsets/" + beatmapset_id

            embed_score = discord.Embed(title="Lien Osu!",
                                        url=osu_link,
                                        color=0xffce54)
            psuedal = " of " + username.capitalize() if username else ""
            embed_score.set_author(name="Map : {}  | score{} :"
                                        "".format(beatmap_id, psuedal))
                                #,icon_url=None)
            #embed_map.set_thumbnail(url=None)

            for score_map in scores:

                user_id = score_map.get('user_id')
                username = score_map.get('username')
                point_player = str(round(float(score_map.get('pp')), 2))
                rank = score_map.get('rank')
                score = score_map.get('score')
                #date = score_map.get('date') # _date_formating

                enabled_mods = __repr__(BeatmapScore(score_map), 'enabled_mods')

                if int(limit) < 7:
                    maxcombo = score_map.get('maxcombo')
                    count50 = score_map.get('count50')
                    count100 = score_map.get('count100')
                    count300 = score_map.get('count300')
                    countmiss = score_map.get('countmiss')
                    countkatu = score_map.get('countkatu')
                    countgeki = score_map.get('countgeki')
                    perfect = score_map.get('perfect')
                    score_stat = ("**Stat :**" + emote_rank +
                                  "\nCombo max : **{}**\nNombre de 50 : "
                                  "{}\nNombre de 100 : {}\n"
                                  "Nombre de 300 : **{}**\nNombre de Miss : "
                                  "**{}**\nNombre de katu : {}\n"
                                  "Nombre de geki : {}\nPerfect : {}\n\n"
                                  "".format(maxcombo, count50, count100,
                                            count300, countmiss, countkatu,
                                            countgeki, "Oui" if perfect == 1 else "Non"))
                else:
                    score_stat = None



                embed_score.add_field(name="{}".format(beatmap_name),
                                      value="{}\n\n"
                                            "**User :** [Profile]({})\n"
                                            "Name : {}\n"
                                            "ID : {}\n\n"
                                            "**Infos :**\n"
                                            "Pp : **{}**{}\n"
                                            "Rank : **{}**\n"
                                            "Score : {}\n"
                                            "Mods : {}\n\n"
                                            "{}"
                                            "".format(osu_direct_link,
                                                      "https://osu.ppy.sh/users/" + user_id,
                                                      username,
                                                      user_id,
                                                      _rank_spacing(point_player),
                                                      emote_star,
                                                      rank,
                                                      _rank_spacing(score),
                                                      enabled_mods,
                                                      score_stat if score_stat else ""
                                                      ), inline=True) #date
            await ctx.send(embed=embed_score)

    @_get.command(aliases=["b"])
    async def beatmap(self, ctx, categorie=None, thing=None):
        """[categorie] [thing] [star_l]

            Parameters :
            ----------
                categorie : str
                    id or set
                    id for beatmap id / set for id of beatmapsets
                thing : str
                    id or beatmapset id
            """
        limit = 10
        if categorie == "set":
            maps = (self._make_req(endpoints.BEATMAPS, dict(
                k=self.key,
                s=thing,
                limit=limit
                )))
        elif categorie == "id":
            maps = (self._make_req(endpoints.BEATMAPS, dict(
                k=self.key,
                b=thing,
                limit=limit
                )))


        if not maps:
            await ctx.send("Il n'y a pas de maps avec en argument `{}`"
                               "".format(thing))
            return

        messaenattente = await ctx.send(self._waiting())
        emotes, error = _get_emote()
        if error:
            await ctx.send(error)
        emote_supporter = emotes.get("OSupporter")
        emote_rank = emotes.get("OsuRank")
        emote_star = emotes.get("OStar")

        mapspec = maps[0]



        #INFOS MAP
        if categorie == "id":
            beatmap_id = thing
        else: beatmap_id = ""

        beatmapset_id = mapspec.get('beatmapset_id')
        osu_link = "https://osu.ppy.sh/beatmapsets/{}#osu/{}".format(beatmapset_id, beatmap_id)



        loop = asyncio.get_event_loop()
        page = loop.create_task(_get_page(osu_link))
        page = await page


        soup = BeautifulSoup(page, 'html.parser')
        info_beatmap = json.loads((soup.find(id="json-beatmapset").string).replace(' ', ''))


        n_map = 0
        if categorie == "id":
            for mappp in info_beatmap.get("beatmaps"):
                iddelamap = mappp.get("id")
                if iddelamap == int(beatmap_id):
                    n_beatmap = n_map
                n_map +=1
        else : n_beatmap = -1

        fail = Image.open(self._get_fail(info_beatmap, n_beatmap)).convert("RGBA")
        cover_map = Image.open(await self._get_cover_map(info_beatmap)).convert("RGBA")

        zoom_y = int(cover_map.size[1]*0.2)# pour pas trop déformer les graphs
        fail = fail.resize((cover_map.size[0], cover_map.size[1]+zoom_y), Image.ANTIALIAS)


        decalage = 25
        decalage_y = 32
        decalage_catego = 40
        dimension_rank = (int(cover_map.size[0]*0.12/2), int((cover_map.size[0]*0.12)/2))

        im_map = Image.new('RGBA', (cover_map.size[0], cover_map.size[1]*3 + zoom_y + decalage_catego*2),  color="#2a2226")
        im_map.paste(cover_map, (0, 0))
        im_map.paste(fail, (0, im_map.size[1]-fail.size[1]))

        bpm_im = Image.open(datapathimages + "bpm.png").convert("RGBA")
        bpm_im = bpm_im.resize(dimension_rank)
        count_circles_im = Image.open(datapathimages + "count_circles.png").convert("RGBA")
        count_circles_im = count_circles_im.resize(dimension_rank)
        time_im = Image.open(datapathimages + "time.png").convert("RGBA")
        time_im = time_im.resize(dimension_rank)
        star_im = Image.open(datapathimages + "star.png").convert("RGBA")
        star_im = star_im.resize(dimension_rank)



        im_map.paste(star_im, (0, cover_map.size[1]  + decalage_catego))
        im_map.paste(time_im, (0, cover_map.size[1] + dimension_rank[1] + decalage + decalage_catego))
        im_map.paste(bpm_im, (0, cover_map.size[1] + dimension_rank[1]*2 + decalage*2 + decalage_catego))
        im_map.paste(count_circles_im, (0, cover_map.size[1] + dimension_rank[1]*3 + decalage*3 + decalage_catego))

        draw_map = ImageDraw.Draw(im_map)


        star = str(info_beatmap.get("beatmaps")[n_beatmap].get("difficulty_rating"))
        bpm = str(info_beatmap.get("bpm"))
        total_length = str(info_beatmap.get("beatmaps")[n_beatmap].get("total_length"))
        max_combo = str(info_beatmap.get("beatmaps")[n_beatmap].get("max_combo")[0])

        nom_diff = info_beatmap.get("beatmaps")[n_beatmap].get("version")

        ics = info_beatmap.get("beatmaps")[n_beatmap].get("cs")
        cs = "cs : " + str(ics)
        idrain = info_beatmap.get("beatmaps")[n_beatmap].get("drain")
        drain = "hp : " + str(idrain)
        iod = info_beatmap.get("beatmaps")[n_beatmap].get("accuracy")
        od = "od : " + str(iod)
        iar = info_beatmap.get("beatmaps")[n_beatmap].get("ar")
        ar = "ar : " + str(iar)

        font_catego2 = _size_text(im_map, star, 0.05)

        star_emplacement = (dimension_rank[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*0.3 + decalage*1.5)
        bpm_emplacement = (dimension_rank[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*1.3 + decalage*2.5)
        total_length_emplacement = (dimension_rank[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*2.3 + decalage*3.5)
        max_combo_emplacement = (dimension_rank[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*3.3 + decalage*4.5)

        #nom_diff_emplacement = ( , )

        cs_emplacement = (int(cover_map.size[0]/3*2), cover_map.size[1] + dimension_rank[1]*0.3 + decalage*1.5)
        drain_emplacement = (int(cover_map.size[0]/3*2), cover_map.size[1] + dimension_rank[1]*1.3 + decalage*2.5)
        od_emplacement = (int(cover_map.size[0]/3*2), cover_map.size[1] + dimension_rank[1]*2.3 + decalage*3.5)
        ar_emplacement = (int(cover_map.size[0]/3*2), cover_map.size[1] + dimension_rank[1]*3.3 + decalage*4.5)

        draw_map.text(star_emplacement, star, font=font_catego2)
        draw_map.text(bpm_emplacement, bpm, font=font_catego2)
        draw_map.text(total_length_emplacement, total_length, font=font_catego2)
        draw_map.text(max_combo_emplacement, max_combo, font=font_catego2)

        #draw_map.text(nom_diff_emplacement, nom_diff, font=font_catego2)

        draw_map.text(cs_emplacement, cs, font=font_catego2)
        draw_map.text(drain_emplacement, drain, font=font_catego2)
        draw_map.text(od_emplacement, od, font=font_catego2)
        draw_map.text(ar_emplacement, ar, font=font_catego2)

        line = int((cover_map.size[0] - (cover_map.size[0]/3*2 + font_catego2.getsize(cs)[0]+ decalage_y*3))/10)

        #dessous ligne
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*0.3 + decalage*1.5 + font_catego2.getsize(cs)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*10,cover_map.size[1] + dimension_rank[1]*0.3 + decalage*1.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=(23,26,28))
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(drain)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*1.3 + decalage*2.5 + font_catego2.getsize(drain)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*10, cover_map.size[1] + dimension_rank[1]*1.3 + decalage*2.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=(23,26,28))
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(od)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*2.3 + decalage*3.5 + font_catego2.getsize(od)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*10, cover_map.size[1] + dimension_rank[1]*2.3 + decalage*3.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=(23,26,28))
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(ar)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*3.3 + decalage*4.5 + font_catego2.getsize(ar)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*10,cover_map.size[1] + dimension_rank[1]*3.3 + decalage*4.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=(23,26,28))

        #ligne cs etc
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*0.3 + decalage*1.5 + font_catego2.getsize(cs)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*ics,cover_map.size[1] + dimension_rank[1]*0.3 + decalage*1.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=self.color)
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(drain)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*1.3 + decalage*2.5 + font_catego2.getsize(drain)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*idrain, cover_map.size[1] + dimension_rank[1]*1.3 + decalage*2.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=self.color)
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(od)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*2.3 + decalage*3.5 + font_catego2.getsize(od)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*iod, cover_map.size[1] + dimension_rank[1]*2.3 + decalage*3.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=self.color)
        draw_map.line((int(cover_map.size[0]/3*2) + font_catego2.getsize(ar)[0] + decalage_y, cover_map.size[1] + dimension_rank[1]*3.3 + decalage*4.5 + font_catego2.getsize(ar)[1]/2, int(cover_map.size[0]/3*2) + font_catego2.getsize(cs)[0] + decalage_y + line*iar,cover_map.size[1] + dimension_rank[1]*3.3 + decalage*4.5 + font_catego2.getsize(cs)[1]/2), width=15, fill=self.color)


        #im_map_save = BytesIO()
        #im_map.save(im_map_save, format='PNG')
        im_map.save(datapath + "temp/cover_map.png", format='PNG')

        url_map, error = self._upload_gyazo(datapath + "/temp/cover_map.png")
        if error:
            await ctx.send(error)
        os.remove(datapath + "/temp/cover_map.png")



        # INFOS CREATOR
        creator = mapspec.get('creator')
        creator_id = str(mapspec.get('creator_id'))
        osu_creator = "https://osu.ppy.sh/users/" + creator_id
        title = mapspec.get('title')
        osu_direct_link = "<osu://dl/{}>".format(beatmapset_id)


        preview_url = "https://" + info_beatmap.get("preview_url")[2:]
        legacy_thread_url = info_beatmap.get("legacy_thread_url") # osu direct / lien map
        dllink = "https://osu.ppy.sh/beatmapsets/{}/download".format(beatmapset_id)


        # EMBED
        beatmap_embed = discord.Embed(title="Mappeur : {}".format(creator),
                                      url=osu_creator,
                                      color=0xfdbe02)

        beatmap_embed.set_author(name="Beatmap Informations : {}".format(title))
                                #, url=None,icon_url=none)
        beatmap_embed.set_image(url=url_map)

        beatmap_embed.add_field(name="Links :",
                                value="Lien site : [Lien Osu!]({})\nLien dl : [télécharger]({})\nOsu!Direct : {}\n[Preview song]({})"
                                      "".format(osu_link, dllink, osu_direct_link, preview_url),
                                inline=True)


        #beatmap_embed.set_thumbnail(url=None)
        await messaenattente.delete()

        await ctx.send(embed=beatmap_embed)

    @_get.command(aliases=["m"])
    async def match(self, ctx, match_id, spe_game=None):
        """<match_id> [game]

        Parameters :
        ----------
        match_id: int
            The ID of the match.
            Correspond to ID that you see in a online multiplayer match summary.
        game: int (optional)
            to get a specific game"""

        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        match_game = (self._make_req(endpoints.MATCH, dict(
            k=self.key,
            mp=match_id)))#, Match))


        if match_game.get('match') == 0:
            await ctx.send('Le match `{}` n\'existe pas'.format(match_id))
        else:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_medal = emotes.get("OsuMedal")

            match = match_game.get('match')

            name = match.get('name')
            start_time = match.get('start_time')
            end_time = match.get('end_time')

            start_time = "Début le : {}".format(_date_formating(start_time))

            if end_time:
                end_time = "Fin le : {}".format(_date_formating(end_time))
            else: end_time = "match encore en cours..."

            if spe_game:
                description = "Partie N°" + spe_game
            else:
                description = "Dernière map jouée :"
            embed_match = discord.Embed(description=description,
                                        #title="Rejoindre la partie",
                                        #url="https://osu.ppy",
                                        color=0x1d5178)
            embed_match.set_author(name="{}'s multiplayers match (ID={})".format(name, match_id))
                                  #,url=...,
                                  #icon_url=author icon)
            embed_match.set_footer(text="{} |--------> {}".format(start_time, end_time))



            games = match_game.get('games') #list mettre un for si plusieurs games
            if games:
                game = games[int(spe_game) if spe_game else -1]
                start_time = game.get('start_time')
                end_time = game.get('end_time')

                beatmap_id = game.get('beatmap_id')
                beatmapset_id, beatmap_name = self._get_beatmapset_id(beatmap_id)

                osu_direct_link = "<osu://dl/{}>".format(beatmapset_id)
                osu_link = "https://osu.ppy.sh/beatmapsets/" + beatmapset_id


                play_mode = game.get('play_mode')
                play_mode = __repr__(Game(game), 'play_mode')

                #game_id = game.get('game_id') // not useful
                #match_type = game.get('match_type') // nobody kwon what that things ~

                scoring_type = game.get('scoring_type')
                scoring_type = __repr__(Game(game), 'scoring_type')

                team_type = game.get('team_type')
                team_type_name = __repr__(Game(game), 'team_type')

                mods = game.get('mods')
                mods = __repr__(Game(game), 'mods')
                if mods == "":
                    mods = "no imposed mods"

                scores = game.get('scores')
                nombre_player = len(scores)

                embed_match.add_field(name=beatmap_name,
                                      value="[Lien de téléchargement Osu!]({})\nOsu!Direct : {}"
                                            "\nMod imposés : {}"
                                            "".format(osu_link,
                                                      osu_direct_link,
                                                      mods),
                                      inline=True)
                embed_match.add_field(name="Infos :",
                                      value="Mode : `{}`"
                                            "\nType de victoire : {}"
                                            "\nType de partie : **{}**"
                                            "\nNombre de partie : **{}**{}"
                                            "".format(play_mode,
                                                      scoring_type,
                                                      team_type_name,
                                                      len(games),
                                                      emote_medal),
                                      inline=True)
                if scores:
                    embed_match.add_field(name="JOUEURS :",
                                          value="Nombre joueur : **{}**".format(nombre_player),
                                          inline=False)

                for user_score in scores:
                    user_id = user_score.get('user_id')
                    username = self._get_username(int(user_id))


                    score = user_score.get('score')
                    passed = "`oui`" + emote_medal if user_score.get("pass") == "1" else "`non`"

                    if team_type in ("2", "3"):
                        color = user_score.get("team")
                        if color == "1":
                            color = "Bleu"
                        else: color = "Rouge"
                        team = "Team : {}".format(color)
                    else: team = ""

                    if nombre_player <= 3:
                        maxcombo = user_score.get('maxcombo')
                        count50 = user_score.get('count50')
                        count100 = user_score.get('count100')
                        count300 = user_score.get('count300')
                        countmiss = user_score.get('countmiss')
                        countgeki = user_score.get('countgeki')
                        countkatu = user_score.get('countkatu')
                        perfect = user_score.get('perfect')
                        enabled_mods = user_score.get('enabled_mods') #  A améliorer shrug

                        score_stat = ("**Stat :**\nMods : {}\nCombo max : **{}**\n"
                                      "Nombre de 50 : {}\nNombre de 100 : {}\n"
                                      "Nombre de 300 : **{}**\nNombre de Miss :"
                                      " **{}**\nNombre de katu : {}\n"
                                      "Nombre de geki : {}\nPerfect : {}\n\n"
                                      "".format(enabled_mods, maxcombo, count50,
                                                count100, count300, countmiss, countkatu,
                                                countgeki, "Oui" if perfect == 1 else "Non"))
                    else:
                        score_stat = ""

                    if username == "SverdWyrd":
                        username += emote_supporter
                    embed_match.add_field(name=username,
                                          value="Score : {}\n"
                                                "Clear : {}\n"
                                                "{}\n\n"
                                                "{}"
                                                "".format(_rank_spacing(score),
                                                          passed,
                                                          team,
                                                          score_stat),
                                          inline=True)
            else:
                games = "Il n'y a pas encore eu de partie"
                embed_match.add_field(name="Match : ", value=games)


            await ctx.send(embed=embed_match)



# ANOTHER COMMANDS

    @commands.command(aliases=["spec"])
    async def spectate(self, ctx, username):
        """<username>
           <username> : str
                username"""
        emotes, error = _get_emote()
        if error:
            await ctx.send(error)
        emote_supporter = emotes.get("OSupporter")
        emote_medal = emotes.get("OsuMedal")
        emote_rank = emotes.get("OsuRank")
        emote_star = emotes.get("OStar")

        if username.lower() == "sverdwyrd":
            emote = emote_supporter
        elif username.lower() == "hitsumo":
            emote = emote_star
        elif username.lower() == "aza":
            emote = emote_rank
        elif username.lower() == "malarne":
            emote = emote_medal
        else:
            emote = ""
        await ctx.send("Observez {0} :{1}\n<osu://spectate/{0}>"
                           "".format(username.capitalize(), emote))


    @commands.group(name="osuemote")
    async def _osuemote(self, ctx):
        """To get help of osuemote commands"""
        #await self.bot.delete_message(ctx.message)
        if ctx.invoked_subcommand is None:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_star = emotes.get("OStar")

            emote_help = discord.Embed(title="Contact me" + emote_star,
                                       url="https://discordapp.com/channels/@me/281798798727184384",
                                       description="To use that commands, "
                                                   "write `[p]osuemote <commands>`",
                                       color=0x8080ff)
            emote_help.set_author(name="Possibles osuemote's group commands")
                                 #, url="")
            #user_help.set_thumbnail(url="")

            emote_help.add_field(name="osuemote create :" + emote_supporter,
                                 value="Create lots of little emotes to make messages look better\n"
                                       "Use emojis slots of the command server (optional)",
                                 inline=True)
            emote_help.add_field(name="osuemote delete :",
                                 value="To delete emotes :c",
                                 inline=False)

            emote_help.set_footer(text="/o/")
            await ctx.send(embed=emote_help)

    @_osuemote.command()
    async def create(self, ctx):
        """[p]osuemote create
            To create emojis (optional)"""
        with open(datapath + 'data.json') as openfile:
            file = json.load(openfile)
            test = file.get("emotes")
        if test:
            server_id = test.get("server_id")
            server = self.bot.get_guild(int(server_id))
            await ctx.send("Les émotes ont déjà été enregistrés "
                               "dans le serveur `{}`".format(server.name))
        else:
            mmssgg = await ctx.send('En cours de création..Veuillez patienter..')
            openfile.close()
            server = ctx.message.guild

            emotes_dict = {} # get all images in path
            for dirpath, dirnames, files in os.walk(datapath + "Images/emotes/"):
                for filename in files:
                    file_short_name = filename.split(".")[0]
                    emotes_dict[dirpath + filename] = file_short_name

            emote_id = {"server_id" : server.id}
            message_emote = ""

            for location, name in emotes_dict.items():
                with open(location, "r+b") as image_file:
                    emoji = await server.create_custom_emoji(name=name, image=image_file.read())
                    emote_def = " <:{}:{}>".format(name, emoji.id)
                    emote_id[name] = emote_def
                    message_emote += emote_def

                file["emotes"] = emote_id

            with open(datapath + 'data.json', 'w') as outfile:
                json.dump(file, outfile)

            await asyncio.sleep(2)

            await mmssgg.delete()
            await ctx.send('Les émotes : {} ont bien été créés'
                               ' dans le serveur : `{}`'.format(message_emote, server.name))

    @_osuemote.command()
    async def delete(self, ctx):
        """osuemote remove
               remove emotes"""
        with open(datapath + 'data.json') as openfile:
            file = json.load(openfile)

        if "emotes" in file:
            emotes = file.get("emotes")
            emotes_id = []
            for emote, value in emotes.items():
                if emote != "server_id":
                    emotes_id.append(re.sub(r" <(:.*:)", "", value)[:-1])
                else:
                    server = self.bot.get_guild(int(value))

            for emote in emotes_id:
                emote = [x for x in list(ctx.guild.emojis) if x.id == int(emote)]
                if emote:
                    emote = emote[0]
                    await emote.delete()

            del file["emotes"]
            with open(datapath + 'data.json', 'w') as outfile:
                json.dump(file, outfile)
            await ctx.send("Les émotes ont bien été supprimés "
                               "du serveur `{}`".format(server.name))
        else:
            await ctx.send('Il n\'y a pas d\'emotes à supprimer')


    @commands.group(name="osukey")
    async def _osukey(self, ctx):
        """To get help of osukey commands"""
        #await self.bot.delete_message(ctx.message)
        if ctx.invoked_subcommand is None:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_medal = emotes.get("OsuMedal")
            emote_star = emotes.get("OStar")

            key_help = discord.Embed(title="Contact me" + emote_star,
                                     url="https://discordapp.com/channels/@me/281798798727184384",
                                     description="To use that commands, "
                                                 "write `[p]osukey <commands>`",
                                     color=0x8080ff)
            key_help.set_author(name="Possibles osukey's group commands")
                                 #, url="")
            #ukey_help.set_thumbnail(url="")

            key_help.add_field(name="osukey add :" + emote_medal,
                               value="Add API keys for the proper functioning of the cog",
                               inline=True)
            key_help.add_field(name="osukey remove :",
                               value="To remove API keys",
                               inline=False)

            key_help.set_footer(text="/o/")
            await ctx.send(embed=key_help)


    @_osukey.command()
    async def add(self, ctx, name, *, key):
        """osukey add <key>

        Parameters :
        ----------
        name : str
            name of the key
        key : str or int
            API key to add
        """
        if name not in ("gyazo", "osu"):
            await ctx.send("Il n'y a pas de clé `{}`. Veuillez rentrer une clé API"
                               " `osu` ou `gyazo`".format(name))
        else:
            with open(datapath + 'data.json') as openfile:
                file = json.load(openfile)
                list_keys = file.get("keys")
                if list_keys:
                    keys = list_keys.get(name)
                    if keys:
                        await ctx.send("La clé `{}` a déjà été enregistrés :\n"
                                           "```{}```".format(name, keys))
                    else:
                        list_keys[name] = key
                        with open(datapath + 'data.json', 'w') as outfile:
                            json.dump(file, outfile)
                        await ctx.send('La clé API `{}` a bien été rajoutée :\n'
                                           '```{}```'.format(name, key))
                        msg = await ctx.send('Reload du cog...')
                        self.bot.unload_extension(self.actual_file)
                        await asyncio.sleep(2)
                        self.bot.load_extension(self.actual_file)
                        await msg.delete()
                        msg = await ctx.send('Cog reload')
                        await asyncio.sleep(3)
                        await msg.delete()

                else:
                    dict_key = {"keys": {
                        name: key
                        }}
                    with open(datapath + 'data.json', 'w') as outfile:
                        json.dump(dict_key, outfile)
                    await ctx.send('La clé API `{}` a bien été rajoutée'
                                       ' :\n```{}```'.format(name, key))
                    msg = await ctx.send('Reload du cog...')
                    self.bot.unload_extension(self.actual_file)
                    await asyncio.sleep(2)
                    self.bot.load_extension(self.actual_file)
                    await msg.delete()
                    msg = await ctx.send('Cog reload')
                    await asyncio.sleep(1)
                    await msg.delete()

    @_osukey.command()
    async def remove(self, ctx, name):
        """osukey remove <key>

        Parameters :
        ----------
        name : str
            name of API key to remove
        """
        if name not in ("gyazo", "osu"):
            await ctx.send("Il n'y a pas de clé `{}`. "
                               "Veuillez rentrer une clé `osu` ou `gyazo`".format(name))
        else:
            with open(datapath + 'data.json') as openfile:
                file = json.load(openfile)
            if "keys" in file:
                keys = file.get("keys")

                if keys.get(name):
                    del keys[name]
                    with open(datapath + 'data.json', 'w') as outfile:
                        json.dump(file, outfile)
                    await ctx.send("La clé API `{}` a bien été supprimé".format(name))
                    msg = await ctx.send('Reload du cog...')
                    self.bot.unload_extension(self.actual_file)
                    await asyncio.sleep(2)
                    self.bot.load_extension(self.actual_file)
                    await msg.delete()
                    msg = await ctx.send('Cog reload')
                    await asyncio.sleep(3)
                    await msg.delete()
                else:
                    await ctx.send('La clé `{}` n\'a pas été renseignée.'.format(name))
            else:
                await ctx.send('Il n\'y a pas de clé à supprimer')



    @commands.command()
    async def save(self, ctx, username=None):
        """save your username"""
        if username:
            with open(datapath + 'data.json') as openfile:
                usersave = json.load(openfile)
                tryp = usersave.get("users")
                if tryp:
                    tryp2 = tryp.get(str(ctx.author.id))
                    if tryp2:
                        tryp[str(ctx.author.id)] = username
                    else:
                        tryp[ctx.author.id] = username
                else:
                    usersave["users"] = {ctx.author.id : username}

            with open(datapath + 'data.json', 'w') as outfile:
                json.dump(usersave, outfile)
            await ctx.send("<@{}>, vous vous êtes bien enregistré en tant que : `{}`".format(ctx.author.id, username))
        else:
            await ctx.send("Veuillez renseigner votre pseudo.")

    @commands.command()
    async def osuhelp(self, ctx):
        """osuhelp
            Get all possibles commands"""
        emotes, error = _get_emote()
        if error:
            await ctx.send(error)
        emote_supporter = emotes.get("OSupporter")
        emote_medal = emotes.get("OsuMedal")
        emote_star = emotes.get("OStar")

        osu_help = discord.Embed(title="Contact me" + emote_star,
                                 url="https://discordapp.com/channels/@me/281798798727184384",
                                 description="To use that commands, write `[p]<commands>`",
                                 color=0x8080ff)
        osu_help.set_author(name="All Osu cog's possibles commands")
                             #, url="")
        #oukey_help.set_thumbnail(url="")
        osu_help.add_field(name="user :",
                           value="-`profile` :\n    Retrieve general user information\n"
                                 "-`best` :\n   Get the top scores for the specified user\n"
                                 "-`recent` :\n"
                                 "Gets the user's ten most recent plays over the last 24 hours",)

        osu_help.add_field(name="get :" + emote_medal,
                           value="-`score` :\n"
                                 "Retrieve information about the"
                                 " top x scores of a specified beatmap\n"
                                 "-`beatmap` :\n   Retrieve general beatmap information\n"
                                 "-`match` :\n   Retrieve information about multiplayer match\n"
                                 "-`replay` :\n   Not implemented.",)

        osu_help.add_field(name="spectate :",
                           value="Create direct link to start spectate user",)

        osu_help.add_field(name="save :",
                           value="To nOt PuT yOuR pSeuDo EaCh TiMes",)
        osu_help.add_field(name="osuemote :",
                           value="-`create` :\n    Create emotes to make messages look better\n"
                                 "-`delete` :\n    Remove emote previously created",
                           inline=False)
        osu_help.add_field(name="osukey :",
                           value="-`add` :\n"
                                 "Add API keys for the proper functioning of the cog\n"
                                 "-`remove` :\n   To remove API key",
                           inline=False)
        osu_help.add_field(name="osuinfo :" + emote_supporter,
                           value="Get all infos of this cog",)
        osu_help.set_footer(text="/o/")

        await ctx.send(embed=osu_help)


    @commands.command()
    async def osuinfo(self, ctx):
        """osuinfo
            Get informations about this cog"""
        emotes, error = _get_emote()
        if error:
            await ctx.send(error)
        emote_supporter = emotes.get("OSupporter")
        emote_medal = emotes.get("OsuMedal")
        emote_star = emotes.get("OStar")
        emote_powi = emotes.get("OPowi")

        osuinfo_help = discord.Embed(title="Contact me" + emote_star,
                                     url="https://discordapp.com/channels/@me/281798798727184384",
                                     color=0x8080ff)
        osuinfo_help.set_author(name="Osu cog's informations")
        osuinfo_help.add_field(name="API keys :",
                               value=""
                                     "Get Osu! API key : [Osu!key](https://osu.ppy.sh/p/api)\n"
                                     "Wiki Osu! API : [Osu!wiki]"
                                     "(https://github.com/ppy/osu-api/wiki)\n\n"
                                     "Get Gyazo API key : [Gyazo key]"
                                     "(https://gyazo.com/oauth/applications)\n"
                                     "Wiki Gyazo API : [Gyazo wiki](https://gyazo.com/api)\n")

        osuinfo_help.add_field(name="Dev :" + emote_medal,
                               value="Python version dev : 3.6.6\n"
                                     "Developed by **`khazhyk`** "
                                     "modified and improved by <@281798798727184384>"
                                     "\nDiscord implementation by <@281798798727184384>\n\n"
                                     "Version : 2\n"
                                     "V1 : January / february 2019\n\n"
                                     "V2 : october -> december 2019")
        osuinfo_help.add_field(name="Others :",
                               value="Thanks to <@!189890795459837952>{} "
                                     "for supporting me and helped in the difficult choices\n"
                                     "Planned at the base for the [Powi server]"
                                     "(https://discord.gg/EyNsdbU){}"
                                     "".format(emote_supporter, emote_powi))
        osuinfo_help.set_footer(text=r"\o/")
        await ctx.send(embed=osuinfo_help)


    @commands.command()
    async def changelog(self, ctx):
        """just wow"""
        osu_changelog = discord.Embed(color=0x222222)
        osu_changelog.set_author(name="Osu!Bot V2 /o/")
        osu_changelog.set_footer(text="Finished december .. 2019")
        url_changelog = "https://cdn.discordapp.com/attachments/309034003980222467/653016223327453193/changelog.png"
        osu_changelog.set_image(url=url_changelog)

        await ctx.send(embed=osu_changelog)




########################## old

    @commands.group(name="olduser", hidden=True)
    async def _olduser(self, ctx):
        """All user's actions possible in Osu!API"""
        #await self.bot.delete_message(ctx.message)
        if ctx.invoked_subcommand is None:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_star = emotes.get("OStar")

            user_help = discord.Embed(title="Contact me" + emote_star,
                                      url="https://discordapp.com/"
                                          "channels/@me/281798798727184384",
                                      description="To use that commands,"
                                                  " write `[p]olduser <commands>`",
                                      color=0x8080ff)
            user_help.set_author(name="Possibles olduser's group commands")
                                 #, url="")
            #user_help.set_thumbnail(url="")

            user_help.add_field(name="olduser oldprofile :",
                                value="Retrieve general user information" + emote_supporter,
                                inline=False)
            user_help.set_footer(text="/o/")
            await ctx.send(embed=user_help)


    @_olduser.command(hidden=True)
    async def oldprofile(self, ctx, username, mode="osu", event_days=31):
        """<username> [mode] [events]

        Parameters :
        ----------
            username : str or int
                username or id_user

            mode : str (optional)
                osu / taiko / ctb / mania. Default to osu

            envents : int (optional)
                x lasts days events. Default to 5 max 31
            """
        if not _key_exist_osu():
            await ctx.send('Merci de renseigner une clé API `osu` valide.')
            return
        if mode == "osu":
            mode = OsuMode.osu
        elif mode == "taiko":
            mode = OsuMode.taiko
        elif mode == "ctb":
            mode = OsuMode.ctb
        elif mode == "mania":
            mode = OsuMode.mania

        user = (self._make_req(endpoints.USER, dict(
            k=self.key,
            u=username,
            type=_username_type(username),
            m=mode.value,
            event_days=event_days
            )))#, JsonList(User)))

        if not user:
            await ctx.send("Le joueur **{}** n'existe pas !".format(username))
        else:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_supporter = emotes.get("OSupporter")
            emote_medal = emotes.get("OsuMedal")
            emote_rank = emotes.get("OsuRank")

            user = user[0]
            user_id = user.get("user_id")
            username = user.get("username")
            join_date = _date_formating(user.get("join_date"))
            playcount = user.get("playcount")
            country = user.get("country")
            total_seconds_played = user.get("total_seconds_played")

            pp_rank = user.get("pp_rank")
            level = user.get("level")
            pp_raw = user.get("pp_raw")
            pp_country_rank = user.get("pp_country_rank")

            count_rank_ss = user.get("count_rank_ss")
            count_rank_ssh = user.get("count_rank_ssh")
            count_rank_s = user.get("count_rank_s")
            count_rank_sh = user.get("count_rank_sh")
            count_rank_a = user.get("count_rank_a")

            events = user.get("events")

            time_play = strftime('%d jours, %HH %Mmn et %Ss', gmtime(int(total_seconds_played)))
            time_play = time_play.replace(str(time_play[0:2]), str(int(time_play[0:2])-1))

            path = datapath + "temp/pp_temp.png"
            level = str(round(float(level), 2)) # arrondi 2 décimals
            pp_raw = str(round(float(pp_raw), 2))

            cercle = float(int(level.split(".")[-1])*360/100)
            plt.figure(figsize=(10, 10))
            axe = plt.subplot()
            axe.invert_xaxis()

            axe.add_patch(Arc((10, 10), 19, 19, -270, linewidth=48, color='dimgrey'))
            axe.add_patch(Arc((10, 10), 19, 19, -270, theta2=cercle, linewidth=48,
                              color='dodgerblue'))
            axe.text(10, 13, r'Level', fontsize=79, color='lawngreen',
                     horizontalalignment='center', #fontfamily='fantasy',
                     fontweight='heavy', verticalalignment='center')
            axe.text(10, 8, level, fontsize=109, color='lawngreen',
                     horizontalalignment='center', #fontfamily='serif',
                     fontweight='heavy', verticalalignment='center')


            axe.plot(10, 10)
            plt.axis('off')
            plt.savefig(path, transparent=True)
            plt.cla()

            url_pp, error = self._upload_gyazo(path)
            if error:
                await ctx.send(error)
            os.remove(path)

            dict_events = {}
            for event in events:
                dict_events[event.get("date")] = event.get("display_html")

            msg = []

            for key, truc in dict_events.items():
                truc = truc.split(username)[-1][9:].capitalize()
                truc = re.sub("(<.>)*", "", truc)
                truc = re.sub("(<..>)*", "", truc)
                truc = re.sub("<.*'>", "", truc)
                truc = re.sub("(\[.*\])", "", truc)


                emote = truc.split(" ")[-1].lower()


                if emote == "medal!":
                    truc += emote_medal
                elif emote == "generosity!" or emote == "supporter!":
                    truc += emote_supporter
                else:
                    truc = truc[:-len(emote)]
                    truc += emote_rank

                date = 'Le **{}** : '.format(_date_formating(key)[:10])
                msg.append("{} {}".format(date, truc))

            del msg[6:]

            if not msg:
                msg.append("Ce joueur n'a pas réalisé d'achievement ces derniers jours")


            #DEF EMBED
            user_embed = discord.Embed(title="Voir le profil",
                                       url="https://osu.ppy.sh/users/" + user_id,
                                       color=0x008000)
            user_embed.set_author(
                name="{}'s profile (ID={})".format(username, user_id))
                                  #    ,icon_url=level)
            user_embed.set_thumbnail(url=url_pp)

            user_embed.add_field(name="Infos :",
                                 value="Pays : {}\nNombre de parties : **{}**\nTemps de jeu : {}"
                                       "".format(country, _rank_spacing(playcount), time_play),
                                 inline=False)
            user_embed.add_field(name="Beatmaps scores :",
                                 value="Nombre de SS+ : **{}**\nNombre de SS : **{}**\n"
                                       "Nombre de S+ : **{}**\nNombre de S : **{}**\n"
                                       "Nombre de A : **{}**\n"
                                       "".format(count_rank_ssh, count_rank_ss,
                                                 count_rank_sh, count_rank_s, count_rank_a),
                                 inline=True)
            user_embed.add_field(name="Score :",
                                 value="Nombre de pp : **{}**\nClassement pays : {}\n"
                                       "Classement monde : {} "
                                       "".format(_rank_spacing(pp_raw),
                                                 _rank_spacing(pp_country_rank),
                                                 _rank_spacing(pp_rank)),
                                 inline=True)

            user_embed.add_field(name="Events ({} jours) :"
                                      "".format(event_days), value="\n".join(msg),
                                 inline=False)

            user_embed.set_footer(text=" A rejoins Osu! le : {}"
                                       "".format(join_date))

            await ctx.send(embed=user_embed)



    @commands.group(name="oldget", hidden=True)
    async def _oldget(self, ctx):
        """All get's actions possible in Osu!API"""
        #await self.bot.delete_message(ctx.message)
        if ctx.invoked_subcommand is None:
            emotes, error = _get_emote()
            if error:
                await ctx.send(error)
            emote_rank = emotes.get("OsuRank")
            emote_star = emotes.get("OStar")

            get_help = discord.Embed(title="Contact me" + emote_star,
                                     url="https://discordapp.com/channels/@me/281798798727184384",
                                     description="To use that commands, write `[p]get <commands>`",
                                     color=0x8080ff)
            get_help.set_author(name="Possibles old get's group commands")
                                 #, url="")
            #user_help.set_thumbnail(url="")


            get_help.add_field(name="oldget oldbeatmap :",
                               value="Retrieve general beatmap information",
                               inline=False)

            get_help.set_footer(text="/o/")
            await ctx.send(embed=get_help)


    @_oldget.command(hidden=True)
    async def oldbeatmap(self, ctx, categorie=None, thing=None, star_l=None, limit_d=None):
        """[categorie] [thing] [star_l] [limit]

            Parameters :
            ----------
                categorie : str
                    id or pack or username
                    id for beatmap id / pack for id of beatmapsets / username for creator
                thing : str
                    id or beatmapset id or username
                star_l: int
                    star limit for the beatmaps to be obtained.
                    All beatmaps displayed will be above this value
                limit : int
                    limit to get x beatmaps in API.
                    Default 10 for pack / 1 for id / 2 for username / 1 for anyelse
                    Max displayed by default : 3
            """

        if categorie == "pack":
            if not limit_d:
                limit = 10
            else: limit = limit_d
            maps = (self._make_req(endpoints.BEATMAPS, dict(
                k=self.key,
                s=thing,
                limit=limit
                )))
        elif categorie == "id":
            if not limit_d:
                limit = 1
            else: limit = limit_d
            maps = (self._make_req(endpoints.BEATMAPS, dict(
                k=self.key,
                b=thing,
                limit=limit
                )))
        elif categorie == "username":
            if not limit_d:
                limit = 2
            else: limit = limit_d
            maps = (self._make_req(endpoints.BEATMAPS, dict(
                k=self.key,
                u=thing,
                limit=limit
                )))
        else:
            if not limit_d:
                limit = 1
            else: limit = limit_d
            maps = (self._make_req(endpoints.BEATMAPS, dict(
                k=self.key,
                limit=limit
                )))#, JsonList(Beatmap)))

        if not maps:
            await ctx.send("Il n'y a pas de maps avec en argument `{}`"
                               "".format(thing))
            return

        emotes, error = _get_emote()
        if error:
            await ctx.send(error)
        emote_supporter = emotes.get("OSupporter")
        emote_rank = emotes.get("OsuRank")
        emote_star = emotes.get("OStar")

        mapspec = maps[0]
        # INFOS CREATOR
        creator = mapspec.get('creator')
        creator_id = mapspec.get('creator_id')
        osu_creator = "https://osu.ppy.sh/users/" + creator_id


        #INFOS MAP
        beatmapset_id = mapspec.get('beatmapset_id')
        #beatmap_id = mapspec.get('beatmap_id') // not useful
        title = mapspec.get('title')
        osu_direct_link = "<osu://dl/{}>".format(beatmapset_id)
        osu_link = "https://osu.ppy.sh/beatmapsets/" + beatmapset_id

        approved = __repr__(Beatmap(mapspec), 'approved')
        genre = __repr__(Beatmap(mapspec), 'genre_id')
        language = __repr__(Beatmap(mapspec), 'language_id')

        mode = __repr__(Beatmap(mapspec), 'mode')
        favourite_count = mapspec.get('favourite_count')
        bpm = mapspec.get('bpm')
        length = mapspec.get('total_length') # With intro / outro
        #hit_length = mapspec.get('hit_length') # Betwen fisrt to last hit

        # EMBED
        beatmap_embed = discord.Embed(title="Creator : {}".format(creator),
                                      url=osu_creator,
                                      color=0xfdbe02)

        beatmap_embed.set_author(name="Beatmap Informations : {}".format(title))
                                #, url=None,icon_url=none)
        beatmap_embed.add_field(name="Links :",
                                value="Lien dl : [Lien Osu!]({})\nOsu!Direct : {}\n\n"
                                      "Nombre de maps : {}\n"
                                      "Limite API : {}"
                                      "".format(osu_link, osu_direct_link, len(maps), limit),
                                inline=True)
        beatmap_embed.add_field(name="General :",
                                value="Mode : `{}`\nStatus : `{}`\nGenre : {}\n"
                                      "Langage : {}\nFavoris : {}{}"
                                      "\n\nBPM : **{}**\nLongueur : **{}** (s)"
                                      "".format(mode, approved, genre,
                                                language, _rank_spacing(favourite_count),
                                                emote_supporter,
                                                bpm, length),
                                inline=True)




        beatmap_embed.set_footer(text="\\o\\")
        #beatmap_embed.set_thumbnail(url=None)

        # Trier les retours API dans l'ordre de -star a +star
        if not star_l:
            star_l = 0
        order = {}
        for beatmap in maps:
            star = beatmap.get('difficultyrating')
            if float(star) > float(star_l):
                number = maps.index(beatmap)
                order[number] = star
        order = [key for (key, value) in sorted(order.items(), key=lambda x: x[1])]
        order = order[:int(limit_d) + 1 if limit_d else 3] # set max result. Default = 3
        order = order[:10] # set max result (no more 10 maps)

        if not order:
            beatmap_embed.add_field(name="EEh mais c'est le vide >~< :",
                                    value="Il n'y a pas de map au dessus de **{}**{}"
                                          "".format(star_l, emote_star if emote_star else " star"),
                                    inline=True)



        number = 0
        for number_get in order:
            number += 1
            beatmap = maps[number_get]
            # OTHERS
            playcount = beatmap.get('playcount')
            passcount = beatmap.get('passcount')
            max_combo = beatmap.get('max_combo')

            version = beatmap.get('version') # difficulty name


            # INFOS GAMEPLAY
            circle_size = beatmap.get('diff_size')
            overall_difficulty = beatmap.get('diff_overall')
            approche_rate = beatmap.get('diff_approach')
            hp_drain = beatmap.get('diff_drain')

            star = beatmap.get('difficultyrating')
            star = str(round(float(star), 2))



            # EMBED
            beatmap_embed.add_field(name="Beatmap {} :".format(number),
                                    value="Star : **{}**{}".format(star, emote_star),
                                    inline=False)

            beatmap_embed.add_field(name="Version : {}".format(version),
                                    value="All users plays : **{}**\nClear : {}\nMax combo : {}"
                                          "".format(_rank_spacing(playcount),
                                                    _rank_spacing(passcount),
                                                    _rank_spacing(max_combo)),
                                    inline=True)

            beatmap_embed.add_field(name="Gameplay infos :" + emote_rank,
                                    value="Circle size : **{}**\nOverall difficulty : **{}**"
                                          "\nApproche rate : **{}**\nHP drain : **{}**"
                                          "".format(circle_size, overall_difficulty,
                                                    approche_rate, hp_drain),
                                    inline=True)


        await ctx.send(embed=beatmap_embed)


def check_folders():
    """Check all folders"""
    if not os.path.exists(datapath + "Images"):
        print("Création du dossier data/osu/ ...")
        os.makedirs(datapath + "Images")

def check_files():
    """Check all files"""
    list_files_py = ['data.json', 'dictmodel.py', 'connectors.py', 'endpoints.py',
                     'enums.py', 'errors.py', 'flags.py', 'model.py', '__init__.py']
    list_files_emotes = ['OSupporterA.gif', 'OsuMedal.png',
                         'OsuRank.png', 'OStar.png', 'OPowi.png']
    list_files_images = ['a.png', 'bpm.png',
                         'count_circles.png', 'playcount.png', 's.png',
                         's_silver.png', 'SS.png', 'SS_silver.png', 'star.png',
                         'stonks.png', 'support.png', 'time.png']

    for file in list_files_py:
        if file == "data.json":
            if not os.path.exists(datapath + file):
                print("Fichier manquant : {}".format(file))
        elif not os.path.exists(datapath.replace("data/", "") + file):
            print("Fichier manquant : {}".format(file))
    for file in list_files_emotes:
        if not os.path.exists(datapath + "Images/emotes/" + file):
            print("Image manquante : {}".format(file))

    for file in list_files_images:
        if not os.path.exists(datapath + "Images/" + file):
            print("Image manquante : {}".format(file))



check_folders()
check_files()
#Die potato : sponsoriseur des emotes // cette ligne est passée comme ligne numéro 2777 pendant un moment, salut Sev
