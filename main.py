import yt_dlp
from discord.ext import commands
import asyncio
import discord
import datetime
import requests


# ТРЯБВА ДА ДОБАВЯ EMBED ЗА СЛЕДВАЩА ПЕСЕН

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

queue = []

offensive_words = ['дебел', 'грозен', 'тъп']


client = commands.Bot(command_prefix='!', intents=discord.Intents.all())


@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))


class MyView(discord.ui.View):
    def __init__(self, voice_client, text_channel, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_pressed = None
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.message = message

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.success)
    async def skip_button(self, interaction: discord.Interaction, button=discord.ui.Button):
        self.voice_client.stop()
        await interaction.response.send_message("Следваща песен")

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.grey)
    async def pause_button(self, interaction: discord.Interaction,  button=discord.ui.Button):
        if self.button_pressed:
            await interaction.response.send_message("Песента вече е паузирана")
        else:
            self.voice_client.pause()
            await interaction.response.send_message("Пауза")

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def resume_button(self, interaction: discord.Interaction, button=discord.ui.Button):
        if self.button_pressed:
            await interaction.response.send_message("Песента вече тече")
        else:
            self.voice_client.resume()
            self.button_pressed = True
            await interaction.response.send_message("Пускане")

    @discord.ui.button(label="Leave 卐", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button=discord.ui.Button):
        await self.voice_client.disconnect()
        await self.message.edit(view=None)
        await interaction.response.send_message("Arrivederci")


async def play_next_song(voice_client, text_channel, message):
    if len(queue) > 0:
        info = queue.pop(0)
        source = await discord.FFmpegOpusAudio.from_probe(info['url'], before_options="-reconnect 1 "
                                                                                      "-reconnect_streamed 1 "
                                                                                      "-reconnect_delay_max 10")
        if source is None:
            await text_channel.send('Не можах да заредя аудиото. Моля опитайте отново.')
            await voice_client.disconnect()
            return
        song_duration = info.get('duration', 0)
        voice_client.play(source, after=lambda x: asyncio.run_coroutine_threadsafe(play_next_song(voice_client,
                                                                                                  text_channel,
                                                                                                  message),
                                                                                   client.loop))
        thumbnail_url = info.get('thumbnail', None)
        embed = discord.Embed(title=f"**{info['title']}**",
                              description=f"Господ изпрати {message.author.mention}, да пусне тази песен",
                              color=discord.Color.blue())
        if song_duration:
            duration = datetime.timedelta(seconds=song_duration)
            embed.add_field(name="Таз песен е ей толко дълга:", value=str(duration), inline=True)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        view = MyView(voice_client, text_channel, message)
        interaction = await text_channel.send(embed=embed, view=view)
        view.message = interaction


@client.command()
async def p(ctx, *, query):
    if ctx.author == client.user:
        return

    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if not voice_client:
        voice = ctx.author.voice
        if not voice:
            await ctx.send("няма никой във войс чата")
            return
        voice_client = await voice.channel.connect()

    with yt_dlp.YoutubeDL({'format': 'bestaudio', 'noplaylist': 'True'}) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
    queue.append(info)
    if not voice_client.is_playing():
        await play_next_song(voice_client, ctx.channel, ctx.message)


@client.command()
async def q(ctx):
    if len(queue) == 0:
        await ctx.send("Queue is empty.")
        return
    embed = discord.Embed(title="Заредени песни", description="Списък:", color=discord.Color.red())
    for i, song in enumerate(queue):
        duration = song.get('duration')
        if duration is not None:
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
        else:
            duration_str = "Непознато"
        embed.add_field(name=f"{i + 1}. {song['title']}", value=f"Duration: {duration_str}", inline=False)

    await ctx.send(embed=embed)


@client.command()
async def pause(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.reply("Пауза")
    else:
        await ctx.reply("Вече е паузирано")


@client.command()
async def skip(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.reply("Следваща песен")
    else:
        await ctx.reply("Плейлистът е празен")


@client.command()
async def resume(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.reply("Музиката продължава")
    else:
        await ctx.reply("Вече се възпроизвежда")


@client.command()
async def helpme(ctx):
    help_embed = discord.Embed(title="Команди", description="Списък на командите:", color=discord.Color.red())
    help_embed.add_field(name="!p 'линк'", value="Пуска песен от YouTube", inline=False)
    help_embed.add_field(name="!pause", value="Паузира вървящата песен", inline=False)
    help_embed.add_field(name="!resume", value="Продължава вървящата песен", inline=False)
    help_embed.add_field(name="!skip", value="Прескача текущата песен и продължава със следващата в Queue-то",
                         inline=False)
    help_embed.add_field(name="!q", value="Показва заредените песни в плейлиста", inline=False)
    help_embed.add_field(name="weather", value="Показва температурата в реално време", inline=False)
    help_embed.add_field(name="time", value="Показва колко е часа", inline=False)
    help_embed.set_footer(text="По бай Тошево време нямаше такива Ботове")
    await ctx.send(embed=help_embed)


@client.command()
async def stop(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        queue.clear()
        voice_client.stop()
        await ctx.reply("Концерта свърши")
    await voice_client.disconnect()


@client.command()
async def leave(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    await voice_client.disconnect()

url = "https://dad-jokes.p.rapidapi.com/random/joke"


@client.event
async def on_message(message):
    if message.content == 'и ловец съм':
        await message.channel.send('и рибаp съм')
    if message.content == 'time':
        now = datetime.datetime.now()
        realtime = now.strftime('%H:%M')
        await message.channel.send(f"Часът е {realtime}.")
    if message.content == 'weather':
        api_url = f'https://api.open-meteo.com/v1/forecast?latitude=42.70&longitude=23.32&current_weather=true&timezone=Europe%2FMoscow'
        response = requests.get(api_url)
        data = response.json()
        if 'current_weather' in data:
            temperature = data['current_weather']['temperature']
            await message.channel.send(f"В момента е {temperature}°C навън")
        else:
            await message.channel.send('Sorry, I could not retrieve the weather data.')
    for word in offensive_words:
        if word in message.content.lower():
            await message.delete()
            await message.channel.send(f"{message.author.mention}, моля, не използвай отново груби думи")
            return
    await client.process_commands(message)
    if message.content == "dad joke":
        headers = {
            "X-RapidAPI-Key": "55c599f48amshbc09d50aed85e7bp13be40jsna35d4003b358",
            "X-RapidAPI-Host": "dad-jokes.p.rapidapi.com"
        }

        response = requests.request("GET", url, headers=headers)

        data = response.json()["body"][0]
        punchline = data["punchline"]

        response_text = f"{data['setup']}\n\n||{punchline}||"

        await message.channel.send(response_text)


client.run('MTA5MDU5NzQyMjIxODA4NDM2Mg.GXT903.bVDTxFCdZ2TRnZQZ6ic64GT6rAK9vSuq9ywhd4')
