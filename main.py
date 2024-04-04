import yt_dlp
from discord.ext import commands
import asyncio
import discord
import datetime


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

queue = []


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
        await interaction.response.send_message("Next song")

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.grey)
    async def pause_button(self, interaction: discord.Interaction,  button=discord.ui.Button):
        if self.button_pressed:
            await interaction.response.send_message("already paused")
        else:
            self.voice_client.pause()
            await interaction.response.send_message("Pause")

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def resume_button(self, interaction: discord.Interaction, button=discord.ui.Button):
        if self.button_pressed:
            await interaction.response.send_message("Already playing")
        else:
            self.voice_client.resume()
            self.button_pressed = True
            await interaction.response.send_message("Playing")

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave_button(self, interaction: discord.Interaction, button=discord.ui.Button):
        await self.voice_client.disconnect()
        await self.message.edit(view=None)
        await interaction.response.send_message("Bye")


async def play_next_song(voice_client, text_channel, message):
    if len(queue) > 0:
        info = queue.pop(0)
        source = await discord.FFmpegOpusAudio.from_probe(info['url'], before_options="-reconnect 1 "
                                                                                      "-reconnect_streamed 1 "
                                                                                      "-reconnect_delay_max 10")
        if source is None:
            await text_channel.send('Can`t load audio, please try again!')
            await voice_client.disconnect()
            return
        song_duration = info.get('duration', 0)
        voice_client.play(source, after=lambda x: asyncio.run_coroutine_threadsafe(play_next_song(voice_client,
                                                                                                  text_channel,
                                                                                                  message),
                                                                                   client.loop))
        thumbnail_url = info.get('thumbnail', None)
        embed = discord.Embed(title=f"**{info['title']}**",
                              description=f"{message.author.mention} requested this song",
                              color=discord.Color.blue())
        if song_duration:
            duration = datetime.timedelta(seconds=song_duration)
            embed.add_field(name="Length of the song:", value=str(duration), inline=True)
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
            await ctx.send("Nobody in voice chat")
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
    embed = discord.Embed(title="Queued songs", description="List:", color=discord.Color.red())
    for i, song in enumerate(queue):
        duration = song.get('duration')
        if duration is not None:
            minutes = duration // 60
            seconds = duration % 60
            duration_str = f"{minutes}:{seconds:02d}"
        else:
            duration_str = "Unknown"
        embed.add_field(name=f"{i + 1}. {song['title']}", value=f"Duration: {duration_str}", inline=False)

    await ctx.send(embed=embed)


@client.command()
async def pause(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await ctx.reply("Pause")
    else:
        await ctx.reply("Already paused")


@client.command()
async def skip(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await ctx.reply("Next song")
    else:
        await ctx.reply("Empty Playlist")


@client.command()
async def resume(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.reply("Music continues")
    else:
        await ctx.reply("Already playing")


@client.command()
async def helpme(ctx):
    help_embed = discord.Embed(title="Commands", description="List of commands:", color=discord.Color.red())
    help_embed.add_field(name="!p 'link'", value="Plays a song", inline=False)
    help_embed.add_field(name="!pause", value="Pause", inline=False)
    help_embed.add_field(name="!resume", value="Resume", inline=False)
    help_embed.add_field(name="!skip", value="Skip to next song",
                         inline=False)
    help_embed.add_field(name="!q", value="Shows the queue", inline=False)
    await ctx.send(embed=help_embed)


@client.command()
async def stop(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        queue.clear()
        voice_client.stop()
        await ctx.reply("End of playlist")
    await voice_client.disconnect()


@client.command()
async def leave(ctx):
    voice_client = discord.utils.get(client.voice_clients, guild=ctx.guild)
    await voice_client.disconnect()


client.run('personal bot key')
