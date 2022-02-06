#!/usr/bin/env python
import logging
import random
import glob
import json
import os

import yt_dlp as youtube_dl
import discord
from discord.ext import commands

logging.basicConfig(filename="farsbot.log", level=logging.DEBUG)

user_id_anders = 801923008532578354;
user_id_fritjof = 560877870076133378;
user_id_kristian = 662052476387721266;
user_id_linus = 151723245366673408;
user_id_max = 140887080048787456;
user_id_nils = 486859100026699789;
user_id_philip = 817454700882296843;
user_id_rickard = 184294174206459904;

ytdl_cfg = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quite': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'outtmpl': 'songcache/%(title)s.%(ext)s',
}

ytdl = youtube_dl.YoutubeDL(ytdl_cfg)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename


def get_sound_with_name(sound_name, base_dir="sounds"):
    return glob.glob("{}/*/{}".format(base_dir, sound_name))[0]

def get_random_fars_sound(sound_dir="", ending=".wav", base_dir="sounds"):
    valid_dirs = next(os.walk(base_dir))[1]
    if sound_dir in valid_dirs:
        return random.choice(glob.glob("{}/{}/*{}".format(base_dir, sound_dir, ending)))
    return random.choice(glob.glob("{}/*/*{}".format(base_dir, ending)))

def get_random_fars_image(img_dir="", ending=".jpg"):
    base_dir = "images"
    valid_dirs = next(os.walk(base_dir))[1]
    if img_dir in valid_dirs:
        return random.choice(glob.glob("{}/{}/*{}".format(base_dir, img_dir, ending)))
    return random.choice(glob.glob("{}/*/*{}".format(base_dir, ending)))

def load_token(filename="token.json"):
    with open(filename) as handle:
        js = json.load(handle)
    return js["token"]

class FarsBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []

    def check_queue(self, client):
        if len(self.queue) > 0:
            fname = self.queue.pop(0)
            client.play(discord.FFmpegPCMAudio(source=fname), after=lambda e: self.check_queue(client))

    @commands.command()
    async def farsljud(self, ctx, category=""):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(get_random_fars_sound(sound_dir=category)))
        client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)

    @commands.command()
    async def farsmusik(self, ctx, category=""):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(get_random_fars_sound(sound_dir=category, ending=".mp3", base_dir="musik")))
        client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)

    @commands.command()
    async def birger_play(self, ctx, url=""):
        if len(url) != 0:
            filename = await YTDLSource.from_url(url, loop=self.bot.loop)
        else:
            filename = self.queue.pop(0)
        client = self.bot.voice_clients[0]
        client.play(discord.FFmpegPCMAudio(source=filename),
            after=lambda e: self.check_queue(client))

    @commands.command()
    async def birger_queue(self, ctx, url=""):
        if len(url) != 0:
            self.queue.append(await YTDLSource.from_url(url, loop=self.bot.loop))
        else:
            str_to_send = "Kön:\n```"
            for f in self.queue:
                base, filename = f.split("/")
                str_to_send += "\t*{0}\n".format(filename)
            str_to_send += "```"
            await ctx.send(str_to_send)

    @commands.command()
    async def birger_skip(self, ctx):
        client = self.bot.voice_clients[0]
        if client.is_playing():
            client.stop()
            if len(self.queue) > 0:
                fname = self.queue.pop(0)
                client.play(discord.FFmpegPCMAudio(source=fname), after=lambda e: self.check_queue(client))
        else:
            if len(self.queue) > 0:
                tmp = self.queue.pop(0)

    @commands.command()
    async def birger_pause(self, ctx):
        client = self.bot.voice_clients[0]
        if client.is_playing():
            client.pause()

    @commands.command()
    async def birger_resume(self, ctx):
        client = self.bot.voice_clients[0]
        if client.is_paused():
            client.resume()

    @commands.command()
    async def birger(self, ctx):
        """
            Shows the api for the music part (birger) of farsbot.
        """
        str_to_send = "Jevvl. Du vill veta hur jag funkar.\n{0}"
        str_to_send = str_to_send.format("```\
!birger_play [youtube url] \n\
!birger_pause \n\
!birger_resume \n\
!birger_queue [youtube url] - för att köa. \n\
!birger_play - utan url för att spela från kön. \n\
!birger_skip för att skippa \n\
!birger_queue utan url för att visa kön.```")
        await ctx.send(str_to_send)

    @commands.command()
    async def fars(self, ctx, category=""):
        await ctx.channel.send(file=discord.File(get_random_fars_image(img_dir=category)))

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)
        await channel.connect()

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if after.channel == None:
            pass
        else:
            if before.channel == None or before.channel.id != after.channel.id:
                if member.bot:
                    pass
                else:
                    soundPath = ""
                    if user_id_anders == member.id:
                        soundPath = get_sound_with_name("vinslov_moven.wav")
                    elif user_id_fritjof == member.id:
                        soundPath = get_sound_with_name("radooradooradooradoo.wav")
                    elif user_id_kristian == member.id:
                        soundPath = get_sound_with_name("Har_du_tur_sa_kommer_det_ett_fax.wav")
                    elif user_id_linus == member.id:
                        soundPath = get_sound_with_name("jövvla_jag_känner.wav")
                    elif user_id_max == member.id:
                        soundPath = get_sound_with_name("campa_i_klaveret_intro.wav")
                    elif user_id_nils == member.id:
                        soundPath = get_sound_with_name("A_har_nat_frunntimmer.wav")
                    elif user_id_philip == member.id:
                        soundPath = get_sound_with_name("Hasten_sa_va_fan.wav")
                    elif user_id_rickard == member.id:
                        soundPath = get_sound_with_name("Nar_hon_var_pa_djurparken.wav")
                    else:
                        soundPath = get_random_fars_sound()

                    client = self.bot.voice_clients[0]
                    src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(soundPath))
                    client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="")
t = load_token()

bot.add_cog(FarsBot(bot))
bot.run(t)


