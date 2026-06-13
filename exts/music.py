import discord
import math
import csv
import os
import re
import asyncio
import edge_tts
import tempfile
import nacl # necessary for opus
# davey included in requirements.txt but doesn't need to be imported (yet)

from discord.ext import commands
from colorama import Fore, Back, Style
from typing import Optional

from utils import *

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}
        self.platforms = ['spotify', 'youtube', 'soundcloud']
        self.tts_queue = asyncio.Queue()
        self.tts_processing = False

    # backend helpers
    # this is to initiate the voice call that the bot will be in
    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state
        return state

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)
    
    async def process_tts_queue(self, voice_state):
        if self.tts_processing:
            return
        
        self.tts_processing = True
        
        # full processing loop
        try:
            while True:
                tts_item = await self.tts_queue.get()
                _tts_text, temp_file_name, _was_playing, _was_paused, _current_song = tts_item
                
                try:
                    # decide whether to mix over music or play tts alone
                    mixer_available = bool(getattr(voice_state, 'mixer', None))
                    music_currently_playing = bool(voice_state.voice and voice_state.voice.is_playing())
                    
                    if not voice_state.voice or not (mixer_available and music_currently_playing):
                        # no active music pipeline – just play tts directly and wait for it to finish
                        source = discord.FFmpegPCMAudio(temp_file_name)
                        done = asyncio.Event()
                        
                        def after_direct(error):
                            try:
                                if os.path.exists(temp_file_name):
                                    os.remove(temp_file_name)
                            except:
                                pass
                            if error:
                                print(f'{Style.BRIGHT}TTS Error{Style.RESET_ALL}: {error}')
                            done.set()
                        
                        voice_state.voice.play(source, after=after_direct)
                        await done.wait()
                    else:
                        # use the mixed audio pipeline, where we add tts on top of currently playing music
                        source = discord.FFmpegPCMAudio(temp_file_name)
                        done_event = voice_state.mixer.start_tts(source)
                        await done_event.wait()
                        try:
                            if os.path.exists(temp_file_name):
                                os.remove(temp_file_name)
                        except:
                            pass
                    
                except Exception as e:
                    # clean up on error
                    try:
                        if os.path.exists(temp_file_name):
                            os.remove(temp_file_name)
                    except:
                        pass
                    print(f'{Style.BRIGHT}TTS Queue Processing Error{Style.RESET_ALL}: {e}')
                
                self.tts_queue.task_done()
                
                if self.tts_queue.empty():
                    break
                
        finally:
            self.tts_processing = False

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member == self.bot.user:
            if before.channel and not after.channel:
                guild_id = before.channel.guild.id
                if guild_id in self.voice_states:
                    voice_state = self.voice_states[guild_id]
                    await voice_state.stop()
                    del self.voice_states[guild_id]


    # commands that are usable
    # join, leave, now, pause, resume, stop, skip, queue, shuffle, remove, moveto, play, grabber, tts
    @commands.command(name='join')
    async def _join(self, ctx: commands.Context):
        destination = ctx.author.voice.channel if ctx.author.voice else None 
        try:
            ctx.voice_state.voice = await destination.connect()
            print(f'{Style.BRIGHT}Joined {Style.RESET_ALL}{Fore.BLUE}{ctx.author.voice.channel.name}{Fore.RESET}')
            return await ctx.message.add_reaction('✅')
        except:
            return await wups(ctx, 'I couldn\'t connect to your voice channel. Maybe you\'re not in one or I\'m in a different one')
      
    @commands.command(name='leave')
    async def _leave(self, ctx: commands.Context):
        if not ctx.voice_state.voice:
            return await wups(ctx, 'I\'m not connected to any voice channel')
        if ctx.voice_client:
            if ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel:
                return await wups(ctx, 'You\'re not in my voice channel')
        
        channel_name = ctx.voice_state.voice.channel.name if ctx.voice_state.voice and ctx.voice_state.voice.channel else "voice channel"
        
        await ctx.voice_state.stop()
        
        if ctx.guild.id in self.voice_states:
            del self.voice_states[ctx.guild.id]
        
        print(f'{Style.BRIGHT}Left {Style.RESET_ALL}{Fore.BLUE}{channel_name}{Fore.RESET}')
        return await ctx.message.add_reaction('👋')

    @commands.command(name='now')
    async def _now(self, ctx: commands.Context):
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            return await ctx.reply(embed=ctx.voice_state.current.create_embed(), mention_author=False)
        else:
            return await wups(ctx, 'I\'m currently not playing anything')

    @commands.command(name='pause')
    async def _pause(self, ctx: commands.Context):
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel or ctx.author.voice is None:
                return await wups(ctx, 'You\'re not in my voice channel')
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing():
            ctx.voice_state.voice.pause()
            return await ctx.message.add_reaction('⏸️')
        else:
            return await wups(ctx, 'Nothing to pause')

    @commands.command(name='resume')
    async def _resume(self, ctx: commands.Context):
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel or ctx.author.voice is None:
                return await wups(ctx, 'You\'re not in my voice channel')
        if ctx.voice_state.is_playing and ctx.voice_state.voice.is_paused():
            ctx.voice_state.voice.resume()
            return await ctx.message.add_reaction('▶️')
        else:
            return await wups(ctx, 'Nothing to resume')

    @commands.command(name='stop')
    async def _stop(self, ctx: commands.Context):
        if ctx.voice_client:
            if ctx.author.voice and ctx.voice_client.channel != ctx.author.voice.channel or ctx.author.voice is None:
                return await wups(ctx, 'You\'re not in my voice channel')
        if ctx.voice_state.is_playing:
            ctx.voice_state.songs.clear()
            ctx.voice_state.voice.stop()
            return await ctx.message.add_reaction('⏹️')
        else:
            return await wups(ctx, 'I\'m not playing any music right now')

    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        voter = ctx.message.author
        djRole = discord.utils.get(ctx.guild.roles, name="DJ")
        if ctx.voice_client:
            if ctx.voice_client.channel != voter.voice.channel or voter.voice is None:
                return await wups(ctx, 'You\'re not in my voice channel')
        if not ctx.voice_state.is_playing:
            return await wups(ctx, 'I\'m not playing any music right now')
        if voter == ctx.voice_state.current.requester or djRole in voter.roles or voter.guild_permissions.administrator:
            ctx.voice_state.skip()
            return await ctx.message.add_reaction('⏭️')
        else:
            return await wups(ctx, 'You didn\'t request this song to be played (DJs and adminstrators are unaffected)')

    @commands.command(name='queue')
    async def _queue(self, ctx: commands.Context, *, page: int = 1):
        if page < 1:
            return await wups(ctx, 'Invalid page number. Must be greater than or equal to `1`')
        if len(ctx.voice_state.songs) == 0:
            return await wups(ctx, 'Queue is empty')
        items_per_page = 10
        pages = math.ceil(len(ctx.voice_state.songs) / items_per_page)
        if page > pages:
            return await wups(ctx, f'Invalid page number. Must be less than or equal to `{pages}`')
        
        start = (page - 1) * items_per_page
        end = start + items_per_page
        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += f'`{i+1}.` **{song.source.title}** (*{song.source.duration}*){'\n' if i != end else ''}'
        embed = (discord.Embed(color=discord.Color.purple(), title=f'**__{len(ctx.voice_state.songs)} Track{'s' if len(ctx.voice_state.songs) > 1 else ''}__**', description=queue)
                .set_footer(text=f'Viewing page {page}/{pages}\nQueue length: {parse_total_duration([song.source.duration for song in ctx.voice_state.songs])}'))
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name='shuffle')
    async def _shuffle(self, ctx: commands.Context):
        author = ctx.message.author
        djRole = discord.utils.get(ctx.guild.roles, name="DJ")

        if ctx.voice_client:
            if ctx.voice_client.channel != author.voice.channel or author.voice is None:
                return await wups(ctx, 'You\'re not in my voice channel')
        if author.guild_permissions.administrator or djRole in author.roles:
            if len(ctx.voice_state.songs) == 0:
                return await wups(ctx, 'Queue is empty')
            else:
                ctx.voice_state.songs.shuffle()
                return await ctx.message.add_reaction('🔀')
        else:
            return await wups(ctx, 'You don\'t have the permissions to use this. Must be either a DJ or administrator')

    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        queue = ctx.voice_state.songs
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel or ctx.author.voice is None:
                return await wups(ctx, 'You\'re not in my voice channel')
        if len(queue) == 0:
            return await wups(ctx, 'Queue is empty')
        elif index < 0 or index == 0 or index > len(queue):
            return await wups(ctx, 'Index out of bounds')
        ctx.voice_state.songs.remove(index - 1)
        return await ctx.message.add_reaction('✅')

    @commands.command(name='moveto')
    async def _moveto(self, ctx: commands.Context, from_index: int, to_index: int):
        queue = ctx.voice_state.songs
        djRole = discord.utils.get(ctx.guild.roles, name="DJ")

        if ctx.voice_client and (ctx.author.voice is None or ctx.voice_client.channel != ctx.author.voice.channel):
            return await wups(ctx, 'You\'re not in my voice channel')
        if not (ctx.author.guild_permissions.administrator or (djRole and djRole in ctx.author.roles)):
            return await wups(ctx, 'You don\'t have the permissions to use this. Must be either a DJ or administrator')

        q_len = len(queue)
        if q_len == 0:
            return await wups(ctx, 'Queue is empty')
        if from_index < 1 or from_index > q_len:
            return await wups(ctx, f'Source index out of bounds (must be between 1 and {q_len})')
        if to_index < 1 or to_index > q_len:
            return await wups(ctx, f'Destination index out of bounds (must be between 1 and {q_len})')
        if from_index == to_index:
            return await wups(ctx, 'Source and destination positions are the same')

        from_pos, to_pos = from_index - 1, to_index - 1
        song = queue._queue[from_pos]
        del queue._queue[from_pos]
        queue._queue.insert(to_pos, song)
        return await ctx.message.add_reaction('✅')

    @commands.command(name='play')
    async def _play(self, ctx: commands.Context, *, search: str):
        if not ctx.voice_state.voice: # bot not in vc at all
            return await wups(ctx, 'I\'m not connected to a voice channel')
        if ctx.voice_client:
            if ctx.author.voice is None: # user not in vc at all but bot is
                return await wups(ctx, 'You\'re not connected to a voice channel')
            elif ctx.voice_client.channel != ctx.author.voice.channel: # user in different vc than bot
                return await wups(ctx, 'I\'m already in a different voice channel')
            
        async with ctx.typing():
            try:
                source = await YTDLSource.create_source(ctx, search)
            except YTDLError as e:
                return await wups(ctx, f'An error occurred while processing this request (`{str(e)}`)')
            else:
                song = Song(source)
                await ctx.voice_state.songs.put(song)
                return await reply(ctx, f'Queued {str(source)}')
            
    @commands.command(name='grabber')
    async def _grabber(self, ctx, platform: str, *query):
        platform_lower = platform.lower()
        if platform_lower not in self.platforms:
            return await wups(ctx, "Invalid platform choice! Must be either `Spotify`, `YouTube`, or `SoundCloud`")

        query, err = MusicDownloadHandlers.normalize_grabber_query(query, platform_lower)
        if err:
            return await wups(ctx, err)

        if await in_channels(ctx, ["wom-shenanigans", "good-tunes"], True):
            async with ctx.typing():
                msg = await ctx.reply("Hang tight! I'll try downloading your song. You'll be pinged with your song once I finish.", mention_author=False)

                if platform_lower == "spotify":
                    spec = MusicDownloadHandlers.spotify(query)
                elif platform_lower == "youtube":
                    spec = MusicDownloadHandlers.youtube(query)
                else:
                    spec = MusicDownloadHandlers.soundcloud(query)

                success, error = await MusicDownloadHandlers.run_download(spec)
                if not success:
                    await msg.delete()
                    return await wups(ctx, error)

                return await MusicDownloadHandlers.send_downloaded_files(ctx, msg)

    @commands.command(name='mix')
    async def _mix(self, ctx: commands.Context, music_volume: Optional[int] = None, tts_volume: Optional[int] = None):
        djRole = discord.utils.get(ctx.guild.roles, name="DJ")
        if not (ctx.author.guild_permissions.administrator or (djRole and djRole in ctx.author.roles)):
            return await wups(ctx, "You don't have the permissions to use this. Must be either a DJ or administrator")

        current_music, current_tts = MusicMixHandlers.load_current_mix_levels()
        mode, music_scalar, tts_scalar, error = MusicMixHandlers.resolve_mix_inputs(music_volume, tts_volume, current_music, current_tts)
        if mode == "current":
            return await reply(ctx, f'Current mix levels — Music: `{int(current_music * 100)}%`, TTS: `{int(current_tts * 100)}%`')
        if mode == "error":
            return await wups(ctx, error)

        MusicMixHandlers.persist_mix_levels(music_scalar, tts_scalar)
        MusicMixHandlers.apply_mix_to_voice_state(ctx.voice_state, music_scalar, tts_scalar)
        return await ctx.message.add_reaction('✅')

    @commands.command(name='voice')
    async def _voice(self, ctx: commands.Context, *, choice: Optional[str] = None):
        if choice is None:
            voice_id = lists["voice"].get(str(ctx.author.id))
            if voice_id is None:
                return await reply(ctx, f"Your TTS voice is the default. Set one with `!w voice (male/female) (1/2/3)`.")
            alias = voice_id_to_alias.get(voice_id, voice_id)
            return await reply(ctx, f"Your TTS voice is **{alias}**!")
        key = choice.strip().lower().replace(" ", "")
        voice_id = tts_voice_aliases.get(key)
        if voice_id is None:
            return await wups(ctx, f"Unknown voice. Use one of: `male 1`, `male 2`, `male 3`, `female 1`, `female 2`, `female 3`")
        set_voice(ctx.author.id, voice_id)
        alias = voice_id_to_alias[voice_id]
        return await reply(ctx, f"Your TTS voice is now **{alias}**!")

    @commands.command(name='tts')
    async def _tts(self, ctx: commands.Context, *, message: str):
        if not ctx.voice_state.voice: # bot not in vc at all
            return await wups(ctx, 'I\'m not connected to a voice channel')
        if ctx.voice_client:
            if ctx.author.voice is None: # user not in vc at all but bot is
                return await wups(ctx, 'You\'re not connected to a voice channel')
            elif ctx.voice_client.channel != ctx.author.voice.channel: # user in different vc than bot
                return await wups(ctx, 'I\'m already in a different voice channel')
        
        success, err = await enqueue_tts_message(ctx, message, self.tts_queue, self.tts_processing, lambda: self.bot.loop.create_task(self.process_tts_queue(ctx.voice_state)))
        
        if not success:
            return await wups(ctx, err)
        return await ctx.message.add_reaction('✅')


async def setup(bot):
    await bot.add_cog(Music(bot))
