#!/usr/bin/env python
import logging
import random
import glob
import json

import discord
from discord.ext import commands

logging.basicConfig(filename="farsbot.log", level=logging.DEBUG)

def sample_soundclip(soundbase="sounds", ending=".wav"):
    return random.choice(glob.glob("{}/*{}".format(soundbase, ending)))

def load_token(filename="token.json"):
    with open(filename) as handle:
        js = json.load(handle)
    return js["token"]

class FarsBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            # ingen kanal i post-event VoiceState => usern lamnade kanalen.
            pass
        else:
            if before.channel == None:
                # combon before.channel == None och after.channel != None 
                # betyder att eventen var att en anvandare connectade.
                client = self.bot.voice_clients[0]
                src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(sample_soundclip()))
                client.play(src, after=lambda e: print('Player error: %s' % e) if e else None)
            
    @commands.command()
    async def play(self, ctx, *):
        client = self.bot.voice_clients[0]
        src = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(sample_soundclip()))
        client.play(src, after=lambda e: print('Player error %s' % e) if e else None)


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description="")
t = load_token()

bot.add_cog(FarsBot(bot))
bot.run(t)


