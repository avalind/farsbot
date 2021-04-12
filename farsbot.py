#!/usr/bin/env python
import logging
import random
import glob
import json

import discord
from discord.ext import commands

logging.basicConfig(filename="farsbot.log", level=logging.DEBUG)

soundbase_cfg = {
    "fars": "sounds", #!farsljud fars eller !farsljud slumpar fram ljudklipp ur sounds
    "mille": "mille", #!farsljud mille slumpar fram ur mille etc.
    "vinslov": "vinslov"
}

# samma princip.
imgbase_cfg = {
    "fars": "fars",
    "nils": "nils"
}

def sample_soundclip(soundbase="sounds", ending=".wav"):
    return random.choice(glob.glob("{}/*{}".format(soundbase, ending)))

def get_random_fars_image(imgbase="fars"):
    return random.choice(glob.glob("{}/*{}".format(imgbase, ".jpg")))

def load_token(filename="token.json"):
    with open(filename) as handle:
        js = json.load(handle)
    return js["token"]

class FarsBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def farsljud(self, ctx, category="fars"):
        if category in soundbase_cfg:
            sbase = soundbase_cfg[category]
        else:
            sbase = "fars"

        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(sample_soundclip(soundbase=sbase)))
        client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)

    @commands.command()
    async def fars(self, ctx, category="fars"):
        if category in imgbase_cfg:
            imbase = imgbase_cfg[category]
        else:
            imbase = "fars"
        await ctx.channel.send(file=discord.File(get_random_fars_image(imgbase=imbase)))

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
                    client = self.bot.voice_clients[0]
                    src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(sample_soundclip()))
                    client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)
            

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="")
t = load_token()

bot.add_cog(FarsBot(bot))
bot.run(t)


