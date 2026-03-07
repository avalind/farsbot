#!/usr/bin/env python
import logging
import random
import glob
import json
import os

import asyncio
import base64
import io
import math

import nest_asyncio
import yt_dlp as youtube_dl
import discord
from discord.ext import commands
from PIL import Image
from systemd import journal
import aiohttp
import re

nest_asyncio.apply()
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("farsbot.log"),
        logging.StreamHandler(),
    ],
)

FAXIFY_PROMPT = "Replace all the faces in the first image with random ones from the second. Each face in the first image should be replaced with exactly one face from the second image. Remove background from the faces in the second image if needed. Do not change anything else in the first image. Make sure all the faces in the first image are replaced. Do not leave any unreplaced face!"
OPENROUTER_MODEL = "bytedance-seed/seedream-4.5"

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
monitored_voice_channel_id = 817453063454851189 

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


def load_openrouter_key(filename="openrouter.json"):
    with open(filename) as handle:
        js = json.load(handle)
    return js["api_key"]


FACE_TILE_MAX = 256


def synthesize_face_grid(faces_dir="faces"):
    image_files = glob.glob("{}/*.*".format(faces_dir))
    if not image_files:
        return None
    images = []
    for f in image_files:
        img = Image.open(f).convert("RGBA")
        img.thumbnail((FACE_TILE_MAX, FACE_TILE_MAX), Image.LANCZOS)
        images.append(img)
    max_w = max(img.width for img in images)
    max_h = max(img.height for img in images)
    cols = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / cols)
    grid = Image.new("RGBA", (cols * max_w, rows * max_h), (0, 0, 0, 0))
    for idx, img in enumerate(images):
        col = idx % cols
        row = idx // cols
        x = col * max_w + (max_w - img.width) // 2
        y = row * max_h + (max_h - img.height) // 2
        grid.paste(img, (x, y))
    return grid


MAX_IMAGE_DIMENSION = 2048


def downscale_image(img, max_dim=MAX_IMAGE_DIMENSION):
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.LANCZOS)
    return img


def image_to_base64_uri(img):
    img = downscale_image(img.copy())
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return "data:image/png;base64,{}".format(b64)


def bytes_to_base64_uri(data):
    img = Image.open(io.BytesIO(data))
    img = downscale_image(img)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return "data:image/png;base64,{}".format(b64)


async def call_openrouter(api_key, image_urls, prompt):
    payload = {
        "model": OPENROUTER_MODEL,
        "modalities": ["image"],
        "messages": [
            {
                "role": "user",
                "content": [
                    *[{"type": "image_url", "image_url": {"url": url}} for url in image_urls],
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    headers = {
        "Authorization": "Bearer {}".format(api_key),
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                logging.error("OpenRouter HTTP %s: %s", resp.status, body[:500])
                return None
            result = await resp.json()
    logging.info("OpenRouter response: %s", result)
    choices = result.get("choices", [])
    if not choices:
        logging.error("OpenRouter returned no choices. Response: %s", result)
        return None
    message = choices[0].get("message", {})
    # Try images field (Gemini-style response)
    images = message.get("images", [])
    if images:
        b64_url = images[0]["image_url"]["url"]
        b64_data = b64_url.split(",", 1)[1]
        return base64.b64decode(b64_data)
    # Try inline base64 in content (Seedream-style response)
    content = message.get("content", "")
    if "data:image" in content:
        b64_url = content.strip()
        b64_data = b64_url.split(",", 1)[1]
        return base64.b64decode(b64_data)
    logging.error("OpenRouter returned no images. Response: %s", result)
    return None


class FarsBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.openrouter_key = load_openrouter_key()
        self._voice_connecting = False

    def check_queue(self, client):
        if len(self.queue) > 0:
            fname = self.queue.pop(0)
            client.play(
                discord.FFmpegPCMAudio(source=fname),
                after=lambda e: self.check_queue(client),
            )

    def get_user_sound(self, user_id):
        """Get the appropriate sound file for a user"""
        if user_id == user_id_anders:
            return get_sound_with_name("vinslov_moven.wav")
        elif user_id == user_id_fritjof:
            return get_sound_with_name("radooradooradooradoo.wav")
        elif user_id == user_id_kristian:
            return get_sound_with_name("Har_du_tur_sa_kommer_det_ett_fax.wav")
        elif user_id == user_id_linus:
            return get_sound_with_name("jövvla_jag_känner.wav")
        elif user_id == user_id_max:
            return get_sound_with_name("campa_i_klaveret_intro.wav")
        elif user_id == user_id_nils:
            return get_sound_with_name("A_har_nat_frunntimmer.wav")
        elif user_id == user_id_philip:
            return get_sound_with_name("Hasten_sa_va_fan.wav")
        elif user_id == user_id_rickard:
            return get_sound_with_name("Nar_hon_var_pa_djurparken.wav")
        elif user_id == user_id_beebop:
            return get_sound_with_name("snickeriet1.wav")
        elif user_id == user_id_niklas:
            return get_sound_with_name("flöjtfars.wav")
        else:
            return get_random_fars_sound()

    @commands.command()
    async def farsljud(self, ctx, category=""):
        if self.bot.voice_clients:
            client = self.bot.voice_clients[0]
            src = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(get_random_fars_sound(sound_dir=category))
            )
            client.play(src, after=lambda e: print("Player error: %s" % e) if e else None)

    @commands.command()
    async def farsmusik(self, ctx, category=""):
        if self.bot.voice_clients:
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
        if self.bot.voice_clients:
            client = self.bot.voice_clients[0]
            src = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(get_sound_with_name("brunnen.mp3"))
            )
            client.play(src, after=lambda e: print("Player error: %s" % e) if e else None)

    @commands.command()
    async def birger_play(self, ctx, url=""):
        if not self.bot.voice_clients:
            return
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
        if not self.bot.voice_clients:
            return
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
        if self.bot.voice_clients:
            client = self.bot.voice_clients[0]
            if client.is_playing():
                client.pause()

    @commands.command()
    async def birger_resume(self, ctx):
        if self.bot.voice_clients:
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
    async def faxify(self, ctx):
        if not ctx.message.reference:
            await ctx.send("Du måste svara på ett meddelande med en bild.")
            return
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        image_url = None
        for att in ref_msg.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                image_url = att.url
                break
        if not image_url:
            for embed in ref_msg.embeds:
                if embed.image:
                    image_url = embed.image.url
                    break
                if embed.thumbnail:
                    image_url = embed.thumbnail.url
                    break
        if not image_url:
            await ctx.send("Kunde inte hitta en bild i det meddelandet.")
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                original_bytes = await resp.read()
        grid_img = synthesize_face_grid()
        if grid_img is None:
            await ctx.send("Inga bilder hittades i faces-mappen.")
            return
        original_uri = bytes_to_base64_uri(original_bytes)
        grid_uri = image_to_base64_uri(grid_img)
        try:
            result_bytes = await call_openrouter(
                self.openrouter_key, [original_uri, grid_uri], FAXIFY_PROMPT
            )
        except Exception as e:
            logging.error("Faxify OpenRouter error: %s", e)
            await ctx.send("Något gick fel med faxifieringen.")
            return
        if not result_bytes:
            await ctx.send("Modellen returnerade ingen bild.")
            return
        await ctx.send(
            file=discord.File(io.BytesIO(result_bytes), filename="faxified.png")
        )

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        logging.info(f"Voice state update: member={member} (bot={member.bot}), before={before.channel}, after={after.channel}")
        # Ignore bot's own voice state changes
        if member.bot:
            return

        # Only monitor the specified voice channel
        if monitored_voice_channel_id is None:
            return

        # User joined the monitored voice channel
        if after.channel and after.channel.id == monitored_voice_channel_id:
            # Only act if they weren't already in this channel
            if not before.channel or before.channel.id != monitored_voice_channel_id:
                # Check if bot is not in this voice channel
                bot_in_channel = any(
                    vc.channel.id == monitored_voice_channel_id for vc in self.bot.voice_clients
                )
                
                if not bot_in_channel:
                    if self._voice_connecting:
                        return
                    self._voice_connecting = True
                    # Bot should join the channel
                    try:
                        voice_client = await after.channel.connect()

                        # Wait a moment for connection to stabilize
                        await asyncio.sleep(0.5)

                        # Determine which sound to play
                        soundPath = self.get_user_sound(member.id)

                        # Play the greeting sound
                        src = discord.PCMVolumeTransformer(
                            discord.FFmpegPCMAudio(soundPath)
                        )
                        voice_client.play(
                            src,
                            after=lambda e: print("Player error: %s" % e) if e else None,
                        )
                    except Exception as e:
                        print(f"Error joining channel: {e}")
                    finally:
                        self._voice_connecting = False
                else:
                    # Bot is already in the channel, just play the sound
                    for vc in self.bot.voice_clients:
                        if vc.channel.id == monitored_voice_channel_id:
                            soundPath = self.get_user_sound(member.id)

                            src = discord.PCMVolumeTransformer(
                                discord.FFmpegPCMAudio(soundPath)
                            )
                            vc.play(
                                src,
                                after=lambda e: print("Player error: %s" % e) if e else None,
                            )
                            break

        # User left the monitored voice channel
        if before.channel and before.channel.id == monitored_voice_channel_id:
            # Only act if they're not still in this channel
            if not after.channel or after.channel.id != monitored_voice_channel_id:
                # Check if bot is in the monitored channel
                for vc in self.bot.voice_clients:
                    if vc.channel.id == monitored_voice_channel_id:
                        # Count non-bot members still in the channel (excluding the one who just left)
                        remaining_users = [m for m in vc.channel.members if not m.bot and m.id != member.id]
                        
                        # If no other users remain, disconnect
                        if len(remaining_users) == 0:
                            await vc.disconnect()
                        break


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


@bot.event
async def on_ready():
    logging.info(f"Bot ready. Guilds: {[g.name for g in bot.guilds]}. Cogs: {list(bot.cogs.keys())}")


async def main():
    t = load_token()

    async with bot:
        await bot.add_cog(FarsBot(bot))
        logging.info(f"Cog added. Listeners: {bot.extra_events}")
        await bot.start(t)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.add_reader(j.fileno(), journal_callback)
    asyncio.ensure_future(main(), loop=loop)
    loop.run_forever()
