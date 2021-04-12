#!/usr/bin/env python
import logging
import random
import glob
import json
import os

import discord
from discord.ext import commands

logging.basicConfig(filename="farsbot.log", level=logging.DEBUG)

def get_random_fars_sound(sound_dir="", ending=".wav"):
    base_dir = "sounds"
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

    @commands.command()
    async def farsljud(self, ctx, category=""):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(get_random_fars_sound(sound_dir=category)))
        client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)

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
                    client = self.bot.voice_clients[0]
                    src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(get_random_fars_sound()))
                    client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)
            

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="")
t = load_token()

bot.add_cog(FarsBot(bot))
bot.run(t)


