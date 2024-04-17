import yt_dlp
from discord.ext import commands
import asyncio
import discord
import datetime


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

TOKEN = ''

queue = []

client = commands.Bot(command_prefix='!', intents=discord.Intents.all(),
                      activity=discord.Activity(type=discord.ActivityType.playing))


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
        if len(queue) > 0:
            await interaction.response.send_message("Следваща песен")
        else:
            await self.voice_client.disconnect()
            await self.message.delete()
            await interaction.response.send_message("Туй то,няя повече")

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.grey)
    async def pause_button(self, interaction: discord.Interaction, button=discord.ui.Button):
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

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button=discord.ui.Button):
        await self.voice_client.disconnect()
        message = interaction.message
        await message.edit(view=None)
        await interaction.response.send_message("As Bojinkata once said: Аааайде")


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
                              description=f"Тая песен я пусна е те тоз човек: {message.author.mention}",
                              color=discord.Color.red())
        if song_duration:
            duration = datetime.timedelta(seconds=song_duration)
            embed.add_field(name="Ей толко време ся ше ни дрънчи в ушите:", value=str(duration), inline=True)
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
    if voice_client.is_playing():
        embed_next = discord.Embed(title="Добавена е нова песен в опашката",
                                   description=f'Следваща песен: "**{info["title"]}**"',
                                   color=discord.Color.green())
        await ctx.send(embed=embed_next)
    else:
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


client.run(TOKEN)
