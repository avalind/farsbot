#!/usr/bin/env python
import logging
import random
import glob
import json
import os

import asyncio
import nest_asyncio
import yt_dlp as youtube_dl
import discord
from discord.ext import commands
from systemd import journal
import re

nest_asyncio.apply()
logging.basicConfig(filename="farsbot.log", level=logging.DEBUG)

user_id_anders = 801923008532578354
user_id_fritjof = 560877870076133378
user_id_kristian = 662052476387721266
user_id_linus = 151723245366673408
user_id_max = 140887080048787456
user_id_nils = 486859100026699789
user_id_philip = 817454700882296843
user_id_rickard = 184294174206459904
user_id_beebop = 325631117837336577
user_id_niklas = 249863311838019585

channel_id_general = 817453063454851185

ytdl_cfg = {
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quite": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "outtmpl": "songcache/%(original_url)s.%(ext)s",
}

ytdl = youtube_dl.YoutubeDL(ytdl_cfg)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )
        if "entries" in data:
            data = data["entries"][0]
        filename = data["title"] if stream else ytdl.prepare_filename(data)
        return filename


def get_sound_with_name(sound_name, base_dir="sounds"):
    return glob.glob("{}/*/{}".format(base_dir, sound_name))[0]


def get_reaction_image_with_name(image_name, base_dir="reactions"):
    return glob.glob("{}/{}".format(base_dir, image_name))[0]


def get_random_fars_sound(sound_dir="", ending=".wav", base_dir="sounds"):
    valid_dirs = next(os.walk(base_dir))[1]
    if sound_dir in valid_dirs:
        return random.choice(glob.glob("{}/{}/*{}".format(base_dir, sound_dir, ending)))
    return random.choice(glob.glob("{}/*/*{}".format(base_dir, ending)))


def get_random_fars_image(img_dir=""):
    base_dir = "images"
    valid_dirs = next(os.walk(base_dir))[1]
    if img_dir in valid_dirs:
        return random.choice(glob.glob("{}/{}/*.*".format(base_dir, img_dir)))
    return random.choice(glob.glob("{}/*/*.*".format(base_dir)))


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
            client.play(
                discord.FFmpegPCMAudio(source=fname),
                after=lambda e: self.check_queue(client),
            )

    @commands.command()
    async def farsljud(self, ctx, category=""):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(get_random_fars_sound(sound_dir=category))
        )
        client.play(src, after=lambda e: print("Player error: %s" % e) if e else None)

    @commands.command()
    async def farsmusik(self, ctx, category=""):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                get_random_fars_sound(
                    sound_dir=category, ending=".mp3", base_dir="musik"
                )
            )
        )
        client.play(src, after=lambda e: print("Player error: %s" % e) if e else None)

    @commands.command()
    async def HA(self, ctx, category=""):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(get_sound_with_name("brunnen.mp3"))
        )
        client.play(src, after=lambda e: print("Player error: %s" % e) if e else None)

    @commands.command()
    async def birger_play(self, ctx, url=""):
        if len(url) != 0:
            filename = await YTDLSource.from_url(url, loop=self.bot.loop)
        else:
            filename = self.queue.pop(0)
        client = self.bot.voice_clients[0]
        client.play(
            discord.FFmpegPCMAudio(source=filename),
            after=lambda e: self.check_queue(client),
        )

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
    async def birger_clean(self, ctx):
        self.queue = []

    @commands.command()
    async def birger_skip(self, ctx):
        client = self.bot.voice_clients[0]
        if client.is_playing() or client.is_paused():
            client.stop()
            if len(self.queue) > 0:
                fname = self.queue.pop(0)
                client.play(
                    discord.FFmpegPCMAudio(source=fname),
                    after=lambda e: self.check_queue(client),
                )
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
        str_to_send = str_to_send.format(
            "```\
!birger_play [youtube url] \n\
!birger_pause \n\
!birger_resume \n\
!birger_queue [youtube url] - för att köa. \n\
!birger_play - utan url för att spela från kön. \n\
!birger_skip för att skippa \n\
!birger_queue utan url för att visa kön. \n\
!birger_clean för att tömma kön.```"
        )
        await ctx.send(str_to_send)

    @commands.command()
    async def fars(self, ctx, category=""):
        await ctx.channel.send(
            file=discord.File(get_random_fars_image(img_dir=category))
        )

    @commands.command()
    async def teamwork(self, ctx, category=""):
        await ctx.channel.send(
            file=discord.File(get_reaction_image_with_name("highfive.png"))
        )

    @commands.command()
    async def highfive(self, ctx, category=""):
        await ctx.channel.send(
            file=discord.File(get_reaction_image_with_name("highfive.png"))
        )

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
                        soundPath = get_sound_with_name(
                            "Har_du_tur_sa_kommer_det_ett_fax.wav"
                        )
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
                    elif user_id_beebop == member.id:
                        soundPath = get_sound_with_name("snickeriet1.wav")
                    elif user_id_niklas == member.id:
                        soundPath = get_sound_with_name("flöjtfars.wav")
                    else:
                        soundPath = get_random_fars_sound()

                    client = self.bot.voice_clients[0]
                    src = discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(soundPath)
                    )
                    client.play(
                        src,
                        after=lambda e: print("Player error: %s" % e) if e else None,
                    )


i = discord.Intents.default()
i.messages = True
i.message_content = True
i.voice_states = True

j = journal.Reader()
j.add_match(_SYSTEMD_UNIT="valheim.service")
j.add_match(_SYSTEMD_UNIT="vrising.service")
j.add_match(_SYSTEMD_UNIT="rust.service")
j.seek_tail()
j.get_previous()


def journal_callback():
    j.process()
    for entry in j:
        asyncio.ensure_future(process(entry))


join_matcher = re.compile(r"(?:ZDOID from )(.*)(?: : )(?:.*:[123456789]\b)")
death_matcher = re.compile(r"(?:ZDOID from )(.*)(?: : )(?:.*:0\b)")

vrising_matcher = re.compile(r"(?:approvedUserIndex.*Character: ')(.*)(?:' connected as ID)")
rust_matcher = re.compile(r"(?:\[Authentication\])(.*)(?: authenticated successfully)")

async def process(event):
    textline = str(event["MESSAGE"])
    join_match = join_matcher.findall(textline)
    death_match = death_matcher.findall(textline)
    vrising_match = vrising_matcher.findall(textline)
    rust_match = rust_matcher.findall(textline)
    if len(join_match) > 0:
        channel = bot.get_channel(channel_id_general)
        await channel.send("{} anslöt till Farsheim".format(join_match[0]))
    if len(death_match) > 0:
        channel = bot.get_channel(channel_id_general)
        await channel.send("{} dog en farsartad död".format(death_match[0]))
    if len(vrising_match) > 0:
        channel = bot.get_channel(channel_id_general)
        if len(vrising_match[0]) > 0:
            await channel.send("{} anslöt till Fars Rising".format(vrising_match[0]))
        else:
            await channel.send("En farsartat namnlös vampyr anslöt till Fars Rising".format(vrising_match[0]))
    if len(rust_match) > 0:
        channel = bot.get_channel(channel_id_general)
        await channel.send("{} anslöt till Farsrost".format(rust_match[0]))


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="",
    intents=i,
)


async def main():
    t = load_token()

    async with bot:
        await bot.add_cog(FarsBot(bot))
        await bot.run(t)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.add_reader(j.fileno(), journal_callback)
    asyncio.ensure_future(main(), loop=loop)
    loop.run_forever()
