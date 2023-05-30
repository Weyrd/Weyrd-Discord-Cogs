import discord
from redbot.core import commands
import re
#import requests
import json
import os
import asyncio
import aiohttp
from aiohttp_requests import requests
from bs4 import BeautifulSoup
import matplotlib.animation as animation
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import matplotlib.pyplot as plt
from gyazo import Api


global datapath
global datapathimages
if os.name == 'nt':
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("\\")[:-1]) +  "/data/osu/"
    datapathimages = "/".join(os.path.dirname(os.path.abspath(__file__)).split("\\")[:-1]) +  "/data/osu/Images/"

else:
    datapath = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1]) +  "/data/osu/"
    datapathimages = "/".join(os.path.dirname(os.path.abspath(__file__)).split("/")[:-1]) +  "/data/osu/Images/"


async def _get_page(url):
    r =  await requests.get(url)
    page =  await r.text()
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

def _beatmap_name(name):
    name = re.sub("\((.*)\)", "", name) #<.*?>
    if len(name) > 25:
        name = re.sub("(\[.*\])", "", name) # :.*?: = tout entre :
        if len(name) > 25:
            name = re.sub("(~.*~)", "", name)
            if len(name) > 25:
                name = name[:20] + "..."
    return name

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



class Listenerosu(commands.Cog):
    def __init__(self, bot, key_osu, key_gyazo):
        self.bot = bot
        self.key_osu = key_osu
        self.gyazo_key = Api(access_token=key_gyazo)
        self.color = (194,194,194)
        self.color_profile = (234,234,234)
        self.loop = asyncio.get_event_loop()

    def _upload_gyazo(self, path):
        """Upload image on gyazo and return link"""
        error = "erreur non reconnu pdtr"
        with open(path, 'rb') as file:
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



        ################## hmmmm
        try:
            locs = list(locs)
            del rank_list[-1]
            del locs[-1]
        except Exception:
            pass

        #plt.yticks(locs, rank_list)

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
        cover_beatmap =  self.loop.create_task(_get_image(cover_beatmap))
        cover_beatmap = await cover_beatmap

        enhancer = ImageEnhance.Brightness(cover_beatmap)
        cover_beatmap = enhancer.enhance(0.7)
        cover_beatmap.filter(ImageFilter.BLUR)
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
        return cover_beatmap_save



    async def beatmap(self, reaction : discord.Reaction, user):
        if not user.bot:
            if reaction.message.content.startswith('https://osu.ppy.sh/beatmapsets'):
                msg = reaction.message.content
                message = reaction.message
                await message.clear_reactions()
                idmap = msg.split("/")[-1]
                msg2 = re.sub(".*beatmapsets/", "", msg).split(" ")
                map = re.sub("#.*", "", msg2[0])

                """link = "https://osu.ppy.sh/api/get_beatmaps?s={}&k={}".format(map, self.key_osu)
                r = requests.get(link).json()
                r = r[0]
                title = _beatmap_name(r["title"])"""

                osu_link = "https://osu.ppy.sh/beatmapsets/{}#osu/{}".format(map, idmap)


                page =  self.loop.create_task(_get_page(osu_link))
                page = await page


                soup = BeautifulSoup(page, 'html.parser')
                info_beatmap = json.loads((soup.find(id="json-beatmapset").string).replace(' ', ''))

                n_beatmap=0

                n_map = 0
                for mappp in info_beatmap.get("beatmaps"):
                    iddelamap = mappp.get("id")
                    if iddelamap == int(idmap):
                        n_beatmap = n_map
                        break
                    n_map +=1


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
                max_combo = str(info_beatmap.get("beatmaps")[n_beatmap].get("max_combo"))

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
                creator = info_beatmap.get('creator')
                creator_id = str(info_beatmap.get('user_id'))
                osu_creator = "https://osu.ppy.sh/users/"
                if creator_id :
                    osu_creator += creator_id

                title = info_beatmap.get('title')
                osu_direct_link = "<osu://dl/{}>".format(map)


                preview_url = "https://" + info_beatmap.get("preview_url")[2:]
                legacy_thread_url = info_beatmap.get("legacy_thread_url") # osu direct / lien map
                dllink = "https://osu.ppy.sh/beatmapsets/{}/download".format(map)


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
                t = await message.channel.send(embed=beatmap_embed)


    async def emote(self, message : discord.Message):
            if message.content.startswith('https://osu.ppy.sh/beatmapsets'):
                emotes, error = _get_emote()
                if error:
                    await message.channel.send(error)
                emote_star = emotes.get("OStar")

                if emote_star:
                    emote_star = re.sub("(<.*:)", "", emote_star)[1:-1]
                    emoji = self.bot.get_emoji(int(emote_star))
                    await message.add_reaction(emoji)
