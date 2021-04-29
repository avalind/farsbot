#!/usr/bin/env python
import logging
import random
import glob
import json
import os

import discord
from discord.ext import commands

logging.basicConfig(filename="farsbot.log", level=logging.DEBUG)

base_dir_sounds = "sounds"
base_dir_images = "images"

user_id_anders = 801923008532578354;
user_id_fritjof = 560877870076133378;
user_id_kristian = 662052476387721266;
user_id_linus = 151723245366673408;
user_id_max = 140887080048787456;
user_id_nils = 486859100026699789;
user_id_philip = 817454700882296843;
user_id_rickard = 184294174206459904;

def get_sound_with_name(sound_name):
    return glob.glob("{}/*/{}".format(base_dir_sounds, sound_name))

def get_random_fars_sound(sound_dir="", ending=".wav"):
    valid_dirs = next(os.walk(base_dir_sounds))[1]
    if sound_dir in valid_dirs:
        return random.choice(glob.glob("{}/{}/*{}".format(base_dir_sounds, sound_dir, ending)))
    return random.choice(glob.glob("{}/*/*{}".format(base_dir_sounds, ending)))

def get_random_fars_image(img_dir="", ending=".jpg"):
    base_dir_images = "images"
    valid_dirs = next(os.walk(base_dir_images))[1]
    if img_dir in valid_dirs:
        return random.choice(glob.glob("{}/{}/*{}".format(base_dir_images, img_dir, ending)))
    return random.choice(glob.glob("{}/*/*{}".format(base_dir_images, ending)))

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


