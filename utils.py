import discord
import random
import time
import os
import csv
import asyncio
import functools
import itertools
import json
import audioop
import re
import tempfile
import edge_tts

from discord.ext import commands
from datetime import datetime, timedelta
from pytz import timezone
from typing import Optional
from colorama import Fore, Style, Back
from aiohttp import ClientSession


# global variable declarations, with 1 exception that mix_settings is a function that defines the default global mix settings
files=["commands", "flairs", "coins", "bank", "voucher", "shell", "bomb", "ticket", "letter", "banana", "karma", "voice"]
file_checks={file:False for file in files}
lists={file:{} for file in files}
user_info={}
snipe_data={item:{} for item in ["content", "author", "id", "attachment"]}
editsnipe_data={item:{} for item in ["content", "author", "id"]}
prev_steal_targets={}
target_counts={}
cooldowns={"roulette":10.0, "howgay":10.0, "which":10.0, "itt":10.0, "react":5.0, "rps":5.0, "8ball":5.0, "clear":5.0, "trivia":25.0, "slots":10.0, "steal":30.0, 'bet':30.0, 'heist':600.0}
last_executed={cooldown:{} for cooldown in cooldowns}
starboard_emoji='<:spuperman:670852114070634527>'
shame_emoji='🪳'
starboard_count=4
zenny='<:zenny:1104179194780450906>'
starttime=None
login_timezone='America/Los_Angeles' # chose timezone as pacific because that's where i am based in
tts_voice_aliases = {
    "male1": "en-US-GuyNeural",
    "male2": "en-US-AndrewMultilingualNeural",
    "male3": "en-US-BrianMultilingualNeural",
    "female1": "en-US-JennyNeural",
    "female2": "en-US-AriaNeural",
    "female3": "en-US-EmmaMultilingualNeural",
}
voice_id_to_alias = {v: f"{k[:-1]} {k[-1]}" for k, v in tts_voice_aliases.items()}
default_tts_voice = "en-US-JennyNeural"
MUTE_TIME_LIMITS = {
    "s": ("seconds", 2419200),
    "m": ("minutes", 40320),
    "h": ("hours", 672),
    "d": ("days", 28),
    "w": ("weeks", 4),
}

def mix_settings(music_volume: Optional[float] = None, tts_volume: Optional[float] = None) -> tuple[float, float]:
    global volume_adjustment, tts_volume_adjustment
    file_path = os.path.join(os.path.dirname(__file__), "csv", "mix.csv")

    if music_volume is None and tts_volume is None:
        music_volume, tts_volume = 0.2, 1.0
        try:
            with open(file_path, "r", newline="") as mix_file:
                reader = csv.DictReader(mix_file)
                row = next(reader, None)
            if row:
                try:
                    music_volume = float(row.get("music", music_volume))
                except (TypeError, ValueError):
                    pass
                try:
                    tts_volume = float(row.get("tts", tts_volume))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass

    try:
        music_volume = float(music_volume)
    except (TypeError, ValueError):
        music_volume = 0.2
    try:
        tts_volume = float(tts_volume)
    except (TypeError, ValueError):
        tts_volume = 1.0

    if music_volume < 0.0:
        music_volume = 0.0
    if music_volume > 1.0:
        music_volume = 1.0
    if tts_volume < 0.0:
        tts_volume = 0.0
    if tts_volume > 1.0:
        tts_volume = 1.0

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", newline="") as mix_file:
        writer = csv.DictWriter(mix_file, fieldnames=["music", "tts"])
        writer.writeheader()
        writer.writerow({"music": f"{music_volume:.3f}", "tts": f"{tts_volume:.3f}"})

    volume_adjustment = music_volume
    tts_volume_adjustment = tts_volume
    return music_volume, tts_volume

volume_adjustment, tts_volume_adjustment = mix_settings()


# one-off helpers
# main.py
# help()
def load_help():
    base_dir = os.path.join(os.path.dirname(__file__), "docs")

    pages_path = os.path.join(base_dir, "help_pages.txt")
    with open(pages_path, "r", encoding="utf-8") as file:
        pages = [line.strip() for line in file if line.strip()]

    helpDict = {}
    for page in pages:
        commands_path = os.path.join(base_dir, f"{page}_commands.txt")
        descriptions_path = os.path.join(base_dir, f"{page}_descriptions.txt")

        commands = []
        descriptions = []

        if os.path.exists(commands_path):
            with open(commands_path, "r", encoding="utf-8") as cfile:
                commands = [line.strip() for line in cfile if line.strip()]

        if os.path.exists(descriptions_path):
            with open(descriptions_path, "r", encoding="utf-8") as dfile:
                descriptions = [line.strip() for line in dfile if line.strip()]

        helpDict[page] = {
            "commands": commands,
            "descriptions": descriptions,
        }

    return helpDict

# on_ready()
def get_login_time(tz: str) -> str:
    return f"Time: {datetime.now(timezone(tz)).strftime('%m/%d/%Y, %I:%M:%S %p')}\nTimezone: {tz}\n"

# admin.py
# mute()
def parse_mute_args(args: str) -> tuple[int, str, str]:
    time_unit = 1
    time_limit = "h"
    reason = args.strip() or "No reason provided"

    match = re.match(r"^\s*(\d+)\s*([smhdw])\s*(.*)$", args or "", re.IGNORECASE)
    if match:
        time_unit = int(match.group(1))
        time_limit = match.group(2).lower()
        reason = match.group(3).strip() or "No reason provided"

    return time_unit, time_limit, reason

async def build_mute_duration(ctx: commands.Context, time_unit: int, time_limit: str) -> Optional[timedelta]:
    if time_unit <= 0:
        return await wups(ctx, "Time duration has to be 1 or higher")
    if time_limit not in MUTE_TIME_LIMITS:
        return await wups(ctx, f"Invalid measure of time. Has to be one of the following: `{', '.join(MUTE_TIME_LIMITS.keys())}`")

    attribute, limit = MUTE_TIME_LIMITS[time_limit]
    if time_unit > limit:
        return await wups(ctx, "Cannot mute member for more than 4 weeks")

    return timedelta(**{attribute: time_unit})

# birthday.py
# birthday()
async def collect_birthday_and_timezone(bot: commands.Bot, ctx: commands.Context) -> tuple[Optional[str], Optional[object], Optional[str]]:
    # birthday
    bday_timeout_text = "Time's up! You didn't provide me with your birthday in time..."
    prompt_data = await prompt_for_message(bot, ctx, 'In the next 30 seconds, give me your birthday in the format "MM-DD"!', 30, bday_timeout_text, timeout_wups=False)
    if prompt_data is None:
        return None, None, bday_timeout_text
    prompt1, bday_message = prompt_data

    try:
        bday = datetime.strptime(bday_message.content, "%m-%d").date().strftime("%m-%d")
    except Exception:
        await bday_message.delete()
        await prompt1.delete()
        return None, None, "Invalid birthday input"
    await bday_message.delete()
    await prompt1.delete()

    # timezone
    tz_timeout_text = "Time's up! You didn't provide me with your timezone in time..."
    prompt_data = await prompt_for_message(bot, ctx, "Now, you have 5 minutes to give me the timezone you are based in. Make sure it is one from [this list](<https://gist.githubusercontent.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568/raw/daacf0e4496ccc60a36e493f0252b7988bceb143/pytz-time-zones.py>)!", 300, tz_timeout_text, timeout_wups=False)
    if prompt_data is None:
        return None, None, tz_timeout_text
    prompt2, tz_message = prompt_data

    try:
        tz_obj = timezone(tz_message.content)
    except Exception:
        await tz_message.delete()
        await prompt2.delete()
        return None, None, "Invalid timezone. Refer to [this list](<https://gist.githubusercontent.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568/raw/daacf0e4496ccc60a36e493f0252b7988bceb143/pytz-time-zones.py>)"

    await tz_message.delete()
    await prompt2.delete()

    update_birthday(ctx.author.id, bday, tz_message.content)
    return bday, tz_obj, None

# music.py
# voice()
def set_voice(userID: int, voice_id: str):
    fieldnames = ['user_id', 'voice']
    found = False
    rows = []
    if os.path.exists('csv/voice.csv'):
        with open('csv/voice.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('user_id') == str(userID):
                    rows.append({'user_id': str(userID), 'voice': voice_id})
                    found = True
                else:
                    rows.append(row)
    if not found:
        rows.append({'user_id': str(userID), 'voice': voice_id})
    os.makedirs('csv', exist_ok=True)
    with open('csv/voice.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list("voice")

# queue()
def parse_total_duration(total_duration: list) -> str:
    all_seconds = 0
    conversion_factors = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    for duration in total_duration:
        if ":" in duration:
            parts = duration.split(":")
            if len(parts) == 4:
                days, hours, minutes, seconds = map(int, parts)
                all_seconds += days * 86400 + hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                all_seconds += hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes, seconds = map(int, parts)
                all_seconds += minutes * 60 + seconds
        else:
            parts = duration.split(", ")
            seconds = 0
            for part in parts:
                value, unit = part.split(" ")
                value = int(value)
                if unit.endswith("s"):
                    unit = unit[:-1]
                seconds += value * conversion_factors[unit]
            all_seconds += seconds

    days, remainder = divmod(all_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = [days, hours, minutes, seconds]
    start_idx = None
    for i, part in enumerate(parts):
        if part != 0:
            start_idx = i
            break
    if start_idx is None or start_idx > 2:
        start_idx = 2

    formatted_parts = [f"{part:02d}" for part in parts[start_idx:]]
    return ":".join(formatted_parts)

# tts()
async def enqueue_tts_message(ctx: commands.Context, raw_message: str, tts_queue, tts_processing: bool, start_processing_fn):
    tts_text = f"{ctx.author.display_name or ctx.author.global_name} said {raw_message}"
    if len(tts_text) > 200:
        return False, 'Message is too long. Please keep it under 200 characters'

    temp_path = None
    try:
        async with ctx.typing():
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_path = temp_file.name
            temp_file.close()

            voice_id = lists["voice"].get(str(ctx.author.id)) or default_tts_voice
            communicate = edge_tts.Communicate(tts_text, voice_id)
            await communicate.save(temp_path)

            was_playing = ctx.voice_state.is_playing and ctx.voice_state.voice.is_playing()
            was_paused = ctx.voice_state.voice.is_paused() if ctx.voice_state.voice else False
            current_song = ctx.voice_state.current if was_playing else None

            await tts_queue.put((tts_text, temp_path, was_playing, was_paused, current_song))

            if not tts_processing:
                start_processing_fn()

        return True, None
    except Exception as e:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        return False, f'An error occurred while generating TTS: `{str(e)}`'

# economy.py
# steal()
def steal_target_tracking(author_id: int, target, update_counts: bool = True) -> bool:
    prev_target = prev_steal_targets.get(author_id)
    prev_count = target_counts.get(author_id, 0)

    if prev_target == target and prev_count <= 2:
        return False

    if not update_counts:
        return True

    if prev_target != target:
        target_counts[author_id] = prev_count + 1
        prev_steal_targets[author_id] = target

    # clamp so it never sticks at 2+ across attempts
    target_counts[author_id] = 0 if target_counts.get(author_id, 0) >= 2 else target_counts.get(author_id, 0)
    return True

# slots()
def slots_tally_and_payout(userID: int, reels: list) -> str:
    count7 = reels.count("7️⃣")
    unique = len(set(reels))
    reels_display = f"{reels[0]} | {reels[1]} | {reels[2]}"

    if count7 == 3:
        add_coins(userID, 500)
        return f"{reels_display}\n**Jackpot**! 500 {zenny}!"

    if unique == 1 and reels[0] != "7️⃣":
        add_coins(userID, 100)
        return f"{reels_display}\nSmall prize! 100 {zenny}!"

    if unique == 2:
        prize = 50 if count7 == 2 else 25
        add_coins(userID, prize)
        prize_msg = f"Two lucky 7's! 50 {zenny}!" if prize == 50 else f"Nice! 25 {zenny}!"
        return f"{reels_display}\n{prize_msg}"

    return f"{reels_display}\nBetter luck next time..."

# fun.py
# emulation()
def load_emulation():
    file_path = os.path.join(os.path.dirname(__file__), "docs", "consoles.txt")
    with open(file_path, "r", encoding="utf-8") as file:
        emuDict = {
            line.strip(): {
                "links": [],
                "instructions": ""
            }
            for line in file if line.strip()
        }
    file_path = os.path.join(os.path.dirname(__file__), "docs", "links.txt")
    with open(file_path, "r", encoding="utf-8") as file:
        for key in emuDict.keys():
            line = file.readline().strip()
            emuDict[key]["links"] = [part.strip() for part in line.split(",")]
    file_path = os.path.join(os.path.dirname(__file__), "docs", "instructions.txt")
    with open(file_path, "r", encoding="utf-8") as file:
        for key in emuDict.keys():
            emuDict[key]["instructions"] = file.readline().strip().replace("\\n", "\n")

    return emuDict

# pokedex()
def build_pokedex_embed(pokemon, data: dict, enc_data: dict, pok_data: dict, index: int, shiny_int: int):
    name = [entry for entry in data["names"] if entry["language"]["name"] == "en"][0]["name"]

    if data["gender_rate"] == -1:
        gender_ratio = "Genderless"
    elif data["gender_rate"] == 8:
        gender_ratio = "100% Female"
    else:
        female_percentage = (data["gender_rate"] / 8) * 100
        male_percentage = 100 - female_percentage
        gender_ratio = f"{male_percentage}% Male / {female_percentage}% Female"

    locations = []
    for entry in enc_data:
        loc = capitalize_string(entry["location_area"]["name"])
        if loc.endswith(" Area"):
            loc = loc[: -len(" Area")]
        locations.append(loc)

    moves = [capitalize_string(entry["move"]["name"]) for entry in pok_data["moves"]]

    embed = discord.Embed(title=f"{name}, #{index}", color=discord.Color.red())
    embed.description = ""

    for i, type_ in enumerate(pokemon.types, 1):
        embed.description += f"**Type {i}**: {capitalize_string(type_)}\n"
    embed.description += "\n"

    for i, ability in enumerate(pokemon.abilities, 1):
        embed.description += (
            f"**Ability {i}**: {capitalize_string(ability.name)}"
            f'{" *(Hidden)*" if ability.is_hidden else ""}\n'
        )
    embed.description += "\n"

    embed.description += f"**Base HP**: {pokemon.base_stats.hp}\n"
    embed.description += f"**Base Attack**: {pokemon.base_stats.attack}\n"
    embed.description += f"**Base Defense**: {pokemon.base_stats.defense}\n"
    embed.description += f"**Base Special Attack**: {pokemon.base_stats.sp_atk}\n"
    embed.description += f"**Base Special Defense**: {pokemon.base_stats.sp_def}\n"
    embed.description += f"**Base Speed**: {pokemon.base_stats.speed}\n"
    embed.description += (
        f"**Base Stat Total**: {pokemon.base_stats.hp + pokemon.base_stats.attack + pokemon.base_stats.defense + pokemon.base_stats.sp_atk + pokemon.base_stats.sp_def + pokemon.base_stats.speed}\n\n"
    )
    embed.description += f"**Base Experience**: {pokemon.base_experience if pokemon.base_experience is not None else 0}\n"
    embed.description += f"**Base Happiness**: {data['base_happiness']}\n"
    embed.description += f"**Capture Rate**: {data['capture_rate']}\n\n"
    embed.description += (
        f"**Egg Groups**: {', '.join(capitalize_string(g['name']) for g in [e for e in data['egg_groups']])}\n"
    )
    embed.description += f"**Gender Ratio**: {gender_ratio}\n\n"

    embed.description += (
        f"**Found At**: {', '.join(str(location) for location in locations) if len(locations) != 0 else 'No Location Data'}\n"
    )
    embed.description += (
        f"**Moves Learned**: {', '.join(str(move) for move in moves) if index != 151 else 'Every Move'}"
    )

    try:
        embed.set_thumbnail(url=pokemon.sprites.front.get("shiny")) if shiny_int == 1 else embed.set_thumbnail(url=pokemon.sprites.front.get("default"))
        footer_text = [entry for entry in data["flavor_text_entries"] if entry["language"]["name"] == "en"][0]["flavor_text"]
        footer_text = " ".join(str(footer_text).split())
        embed.set_footer(text=footer_text)
    except Exception:
        pass

    if shiny_int != 1:
        return embed, None
    return embed, f"Woah! A Shiny {name}! ✨"

# roulette()
async def roulette_spin(ctx: commands.Context, target: discord.Member, self_fired: bool, chance: int):
    if random.randint(1, chance) == 1:
        await target.edit(timed_out_until=discord.utils.utcnow() + timedelta(hours=1), reason="roulette")
        return await reply(ctx, f"🔥🔫 {'You' if self_fired else target.name} died! (muted for 1 hour)")

    add_coins(target.id, 1)
    who = "you" if self_fired else "they"
    give = "Here's" if self_fired else "I gave them"
    return await reply(ctx, f"🚬🔫 Looks like {who}'re safe, for now... {give} 1 {zenny} as a pity prize...")

# misc.py
# uptime()
def get_uptime_text():
    start = starttime
    delta = datetime.now(timezone(login_timezone)) - start
    total_seconds = max(0, int(delta.total_seconds()))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    if days:
        return f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"
    if hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"

# currency()
async def get_rate(ctx: commands.Context, from_curr: str, to_curr: str) -> float | None:
    session = ClientSession()
    url = f"https://api.frankfurter.dev/v1/latest?base={from_curr}&symbols={to_curr}"
    async with ctx.typing():
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            await session.close()
            return data["rates"].get(to_curr)


# all sorts of classes for specific functions
# on_message() handler class
class MessageHandlers:
    @staticmethod
    async def custom_commands(message, lists):
        # handle custom commands from lists["commands"]
        if message.content.startswith("!w "):
            parts = message.content.split()
            if len(parts) > 1 and parts[1] in lists["commands"]:
                await message.reply(lists["commands"][parts[1]], mention_author=False)
    
    @staticmethod
    async def phrase_triggers(message):
        # handle exact phrase matches like 'skill issue', 'me', etc
        from random import choice
        
        content = message.content.strip().lower()
        
        if content == "skill issue":
            await message.channel.send(file=discord.File("img/skill-issue.gif"))
        elif content == "me":
            await message.channel.send('<:WoM:836128658828558336>')
        elif content == "which":
            if assert_cooldown("which", message.author.id) == 0:
                members = [m.display_name.lower() for m in message.guild.members if not m.bot]
                await message.channel.send(choice(members))
            else:
                await shark_react(message)
        elif content == "hi guys":
            try:
                await message.add_reaction("🍅")
            except:
                pass
    
    @staticmethod
    async def trigger_reactions(message, triggers, trigger_emojis):
        # handle emoji reactions based on trigger words
        from re import escape, search
        
        if message.channel.name in ['venting', 'serious-talk']:
            return
        
        content_lower = message.content.lower()
        for trigger, emoji in zip(triggers, trigger_emojis):
            if trigger == "persona" and message.channel.name == "the-velvet-room":
                continue
            
            pattern = r'\b' + escape(trigger) + r'\b'
            if search(pattern, content_lower):
                try:
                    await message.add_reaction(emoji)
                except:
                    pass
    
    @staticmethod
    async def shiny_spawn(message, zenny):
        # handle rare shiny spawns
        from random import randint
        
        if message.channel.name in ['venting', 'serious-talk']:
            return
        
        if randint(1, 8192) == 1:
            direct_to_bank(message.author.id, 500)
            with open("img/shiny.png", "rb") as f:
                file = discord.File(f)
                await message.channel.send(
                    content=f"{message.author.name} stumbled across 500 {zenny} and a wild Wyvern of Marina! ✨",
                    file=file
                )
    
    @staticmethod
    async def ping_responses(message, reply_choices, reactions):
        # handle ping interactions
        from re import compile, IGNORECASE
        from random import choice
        import asyncio
        
        wom = discord.utils.get(message.guild.members, bot=True, name="Wyvern of Marina")
        if not wom:
            return
        
        content = message.content.strip()
        
        # "is this true" pattern
        the_thing = compile(rf"<@!?{wom.id}>\s+is this true[\s\?\!\.\,]*$", IGNORECASE)
        if the_thing.fullmatch(content):
            if wom.nick and wom.nick.lower() == "wrok":
                if assert_cooldown("itt", message.author.id) == 0:
                    async with message.channel.typing():
                        await asyncio.sleep(1)
                        await message.reply(choice(reply_choices), mention_author=False)
                else:
                    await shark_react(message)
            else:
                await shark_react(message)
                await message.reply("Wups! I need to be nicknamed \"Wrok\" for this to work...", mention_author=False)
            return
        
        # general ping pattern
        the_thing2 = compile(rf"<@!?{wom.id}>\s+.+", IGNORECASE)
        if the_thing2.fullmatch(content):
            if assert_cooldown("react", message.author.id) == 0:
                async with message.channel.typing():
                    await asyncio.sleep(3)
                    await message.reply(choice(reactions), mention_author=False)
            else:
                await shark_react(message)

# use() handler class
class EconomyUseHandlers:
    @staticmethod
    async def handle(bot: commands.Bot, ctx: commands.Context, item: str):
        if item == "bomb":
            return await EconomyUseHandlers._use_bomb(ctx, item)
        if item == "ticket":
            return await EconomyUseHandlers._use_ticket(bot, ctx, item)
        if item == "letter":
            return await EconomyUseHandlers._use_letter(bot, ctx, item)
        if item == "shell":
            return await EconomyUseHandlers._use_shell(ctx, item)
        if item == "banana":
            return await EconomyUseHandlers._use_banana(ctx, item)
        return await wups(ctx, "Invalid item")

    @staticmethod
    async def _use_bomb(ctx: commands.Context, item: str):
        if subtract_item(item, ctx.author.id, 1):
            target_id = random.choice([key for key in lists["bank"].keys() if not key == str(ctx.author.id)])
            balance = int(lists["bank"][target_id])
            target_id = int(target_id)
            stolen = balance // 2
            member = discord.utils.get(ctx.guild.members, id=target_id)
            if stolen_funds(target_id, stolen):
                direct_to_bank(ctx.author.id, stolen)
                return await reply(ctx, f"Stole {stolen} {zenny} from {member.name}'s bank account! That {zenny} has been deposited into your bank account!")
        return await wups(ctx, f"You don't have a {item}")

    @staticmethod
    async def _use_ticket(bot: commands.Bot, ctx: commands.Context, item: str):
        if subtract_item(item, ctx.author.id, 1):
            prompt_data = await prompt_for_message(bot, ctx, "You have 60 seconds to name your new custom role! This can be done by simply sending the name of that role in this channel. Be aware, however, that the next message you send will be the role name...", 60, "Time's up! You didn't provide me with a role name, so I've given you your ticket back. Try again later...")
            if prompt_data is None:
                add_item(item, ctx.author.id, 1)
                return None
            _, msg = prompt_data
            name = msg.content
            role = await ctx.guild.create_role(name=name)
            await ctx.author.add_roles(role)
            return await msg.reply("Congrats on your new role!")
        return await wups(ctx, f"You don't have a {item}")

    @staticmethod
    async def _use_letter(bot: commands.Bot, ctx: commands.Context, item: str):
        if subtract_item(item, ctx.author.id, 1):
            prompt_data = await prompt_for_message(bot, ctx, "You have 30 seconds to give me the name of a member you want to send a letter to! Your next message in this channel is what I will use to find the member's name!", 30, f"Time's up! You didn't provide me with anyone's name, so I've given you back your {item}...")
            if prompt_data is None:
                add_item(item, ctx.author.id, 1)
                return
            _, msg = prompt_data
            recipient = discord.utils.get(ctx.guild.members, name=str(msg.content).strip())
            try:
                recipient = await commands.MemberConverter().convert(ctx, str(msg.content).strip())
            except commands.BadArgument:
                pass
            if recipient is None or recipient.bot or recipient == ctx.author:
                add_item(item, ctx.author.id, 1)
                await msg.delete()
                return await wups(ctx, f"Invalid member name. I've refunded you your {item}")

            prompt_data = await prompt_for_message(bot, ctx, "Great! Now you have 2 minutes to cook up your letter to this person. Your next message in this channel will dictate that!", 120, f"Time's up! You didn't provide me with any content, so I've given you back your {item}...")
            if prompt_data is None:
                add_item(item, ctx.author.id, 1)
                return await msg.delete()
            _, content = prompt_data
            content_replaced = str(content.content).replace("'", "\\'").replace('"', '\\"')

            await msg.delete()
            try:
                await recipient.send(f"__{ctx.author.name} sent you the following letter!__\n'{content_replaced}'")
            except Exception:
                await ctx.guild.system_channel.send(f"Since {recipient.mention} won't allow me to DM them, I guess I'll just have to air out to the entire world their letter from {ctx.author.name}...\n\n'{content_replaced}'")
            await content.reply("Message sent!")
            return await content.delete()
        return await wups(ctx, f"You don't have a {item}")

    @staticmethod
    async def _use_shell(ctx: commands.Context, item: str):
        if subtract_item(item, ctx.author.id, 1):
            target = random.choice([member for member in ctx.guild.members if not member.bot and not member == ctx.author])
            balance = int(lists["coins"][str(target.id)])
            if balance % 2 == 1:
                add_coins(target.id, 1)
                balance = int(lists["coins"][str(target.id)])
            if subtract_coins(target.id, int(balance // 2)):
                add_coins(ctx.author.id, int(balance // 2))
                return await reply(ctx, f"{target.name} got hit by a {item}! You received {balance // 2} {zenny} from them!")
        return await wups(ctx, f"You don't have a {item}")

    @staticmethod
    async def _use_banana(ctx: commands.Context, item: str):
        if subtract_item(item, ctx.author.id, 1):
            msg = await ctx.reply("You ate a banana! You feel something funny inside your body...")
            await asyncio.sleep(3)
            return await msg.edit(content="Turns out that was just your stomach growling. The banana you just ate was a regular old banana...", allowed_mentions=discord.AllowedMentions.none())
        return await wups(ctx, f"You don't have a {item}")

# grabber() handler class
class MusicDownloadHandlers:
    @staticmethod
    def spotify(query: str) -> dict:
        return {
            "cmd": f'spotdl download "{query}" --format mp3 --output "{{artist}} - {{title}}.{{output-ext}}" --lyrics synced --use-official-api',
            "name": "Spotify",
            "colors": (Fore.BLACK, Back.GREEN),
            "error_checks": {"LookupError": "I couldn't find a song on Spotify with that query. Try again"},
        }

    @staticmethod
    def youtube(query: str) -> dict:
        return {
            # feel free to change the browser if you want to test, but then change back to firefox once finished testing as that is the browser neel's server relies on. MAKE SURE YOU ARE SIGNED INTO YOUTUBE ON YOUR BROWSER WITH THE ASSOCIATED COOKIES!
            "cmd": f'yt-dlp {query} -x --audio-format mp3 -o "%(title)s.%(ext)s" --no-playlist --embed-metadata --embed-thumbnail --remote-components ejs:github --cookies-from-browser firefox', 
            "name": "YouTube",
            "colors": (Fore.WHITE, Back.RED),
            "error_checks": {"Downloading 0 items": "I couldn't download anything. Try again (Most likely, your search query was invalid.)"},
        }

    @staticmethod
    def soundcloud(query: str) -> dict:
        return {
            "cmd": f"scdl -l {query} --onlymp3 --force-metadata --no-playlist",
            "name": "SoundCloud",
            "colors": (Fore.WHITE, Back.LIGHTRED_EX),
            "error_checks": {
                "Found a playlist": "I don't want to bombard you with pings! Try downloading songs individually",
                "URL is not valid": "Invalid URL! Try again",
            },
        }

    @staticmethod
    async def run_download(download_spec: dict):
        cmd = download_spec["cmd"]
        name = download_spec["name"]
        colors = download_spec["colors"]
        error_checks = download_spec.get("error_checks")

        print(f"{Style.BRIGHT}Downloading from {colors[0]}{colors[1]}{name}{Fore.RESET}{Back.RESET}{Style.RESET_ALL}...")
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str, stderr_str = stdout.decode(), stderr.decode()
        print(f"{Style.BRIGHT}Out{Style.RESET_ALL}:\n{stdout_str}{Style.BRIGHT}Err{Style.RESET_ALL}:\n{stderr_str}\n")

        if error_checks:
            for check, error_msg in error_checks.items():
                if check in stdout_str or check in stderr_str:
                    return False, error_msg

        if proc.returncode != 0:
            return False, "I couldn't download anything. Try again"
        return True, None

    @staticmethod
    async def send_downloaded_files(ctx, msg):
        """Send downloaded MP3 files and clean up."""
        new_files = [f for f in os.listdir(".") if f.endswith(".mp3")]
        for file in new_files:
            file_path = os.path.join(".", file)
            try:
                await ctx.reply(content="Here is your song!", file=discord.File(file_path))
            except Exception:
                os.remove(file_path)
                await msg.delete()
                return await wups(ctx, "The file was too big for me to send")
            os.remove(file_path)
        return await msg.delete()


    @staticmethod
    def normalize_grabber_query(query_parts, platform_lower: str) -> tuple[Optional[str], Optional[str]]:
        query = " ".join(query_parts)
        if not query:
            return None, "I need a search query"

        # remove wrappers for embedded links
        if query[0] == "<" and query[-1] == ">":
            query = query[1:-1]
        elif query[0] == "[" and query[-1] == ")":
            return None, "I couldn't download anything in an embedded link. Try again"

        # remove spotify-ish tracking param
        query = re.sub(r"[?&]si=[a-zA-Z0-9_-]+", "", query)

        # extra normalization for each supported platform
        if platform_lower == "youtube":
            youtube_url_pattern = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/)|youtu\.be/|m\.youtube\.com/watch\?v=)"
            if not re.search(youtube_url_pattern, query):
                return f'ytsearch:"{query}"', None
            return query, None

        if platform_lower == "soundcloud":
            if not query.startswith("https://soundcloud.com/"):
                return None, "I couldn't download anything. Try again (Due to API requirements, you must make sure that you are providing a `https://soundcloud.com/` link as your query.)"
            query = query[:query.find("?in=")] if "?in=" in query else query
            return query.rstrip("/"), None

        return query, None

# mix() handler class
class MusicMixHandlers:
    @staticmethod
    def load_current_mix_levels() -> tuple[float, float]:
        global volume_adjustment, tts_volume_adjustment
        current_music = volume_adjustment
        current_tts = tts_volume_adjustment

        mix_path = os.path.join(os.path.dirname(__file__), "csv", "mix.csv")
        try:
            with open(mix_path, "r", newline="") as mix_file:
                reader = csv.DictReader(mix_file)
                row = next(reader, None)
                if row:
                    current_music = float(row.get("music", current_music))
                    current_tts = float(row.get("tts", current_tts))
        except Exception:
            pass

        return current_music, current_tts

    @staticmethod
    def resolve_mix_inputs(music_volume: Optional[int], tts_volume: Optional[int], current_music: float, current_tts: float) -> tuple[str, Optional[float], Optional[float], Optional[str]]:
        if music_volume is None and tts_volume is None:
            return "current", None, None, None

        if (music_volume is None) != (tts_volume is None):
            return "error", None, None, "Please specify two different volume percentages, e.g. `!w mix 35 100`"

        current_music_percent = int(current_music * 100)
        current_tts_percent = int(current_tts * 100)

        if music_volume is None:
            music_volume = current_music_percent
        if tts_volume is None:
            tts_volume = current_tts_percent

        try:
            music_volume = int(music_volume)
            tts_volume = int(tts_volume)
        except (TypeError, ValueError):
            return "error", None, None, "Please provide whole numbers between 0 and 100 for both values"

        if not (0 <= music_volume <= 100) or not (0 <= tts_volume <= 100):
            return "error", None, None, "Please keep both values between 0 and 100"

        music_scalar = music_volume / 100.0
        tts_scalar = tts_volume / 100.0

        # Preserve original clamping behavior.
        if music_scalar < 0.0:
            music_scalar = 0.0
        if music_scalar > 1.0:
            music_scalar = 1.0
        if tts_scalar < 0.0:
            tts_scalar = 0.0
        if tts_scalar > 1.0:
            tts_scalar = 1.0

        return "apply", music_scalar, tts_scalar, None

    @staticmethod
    def persist_mix_levels(music_scalar: float, tts_scalar: float) -> None:
        global volume_adjustment, tts_volume_adjustment

        mix_path = os.path.join(os.path.dirname(__file__), "csv", "mix.csv")
        os.makedirs(os.path.dirname(mix_path), exist_ok=True)

        volume_adjustment = music_scalar
        tts_volume_adjustment = tts_scalar

        with open(mix_path, "w", newline="") as mix_file:
            writer = csv.DictWriter(mix_file, fieldnames=["music", "tts"])
            writer.writeheader()
            writer.writerow({"music": f"{music_scalar:.3f}", "tts": f"{tts_scalar:.3f}"})

    @staticmethod
    def apply_mix_to_voice_state(voice_state, music_scalar: float, tts_scalar: float) -> None:
        if voice_state and getattr(voice_state, "mixer", None):
            voice_state.mixer.music_volume_when_tts = music_scalar
            voice_state.mixer.tts_volume_when_mixed = tts_scalar

# trivia handler class
class TriviaHandlers:
    TRIVIA_TYPES = ["general", "film", "music", "tv", "games", "anime"]
    TRIVIA_CATEGORIES = [9, 11, 12, 14, 15, 31]

    @staticmethod
    def resolve_trivia_category(type: Optional[str]) -> tuple[Optional[int], Optional[str]]:
        if type is None:
            return random.choice(TriviaHandlers.TRIVIA_CATEGORIES), None

        t = type.lower()
        if t not in TriviaHandlers.TRIVIA_TYPES:
            return None, "Invalid trivia type"

        idx = TriviaHandlers.TRIVIA_TYPES.index(t)
        return TriviaHandlers.TRIVIA_CATEGORIES[idx], None

    @staticmethod
    def fetch_trivia(category_id: int) -> tuple[str, str, list[str]]:
        import requests
        import urllib.parse

        response = requests.get(
            f"https://opentdb.com/api.php?amount=1&category={category_id}&type=multiple&encode=url3986"
        )
        data = json.loads(response.text)
        question = urllib.parse.unquote(data["results"][0]["question"])

        correct_answer = urllib.parse.unquote(data["results"][0]["correct_answer"])
        incorrect_answers = data["results"][0]["incorrect_answers"]
        options = [urllib.parse.unquote(answer) for answer in incorrect_answers] + [correct_answer]
        random.shuffle(options)

        return question, correct_answer, options

    @staticmethod
    def build_trivia_embed(question: str, options: list[str]) -> discord.Embed:
        quiz_embed = discord.Embed(title="❓ Trivia ❓", description=question, color=discord.Color.purple())
        quiz_embed.add_field(name="Options", value="\n".join(options), inline=False)
        quiz_embed.set_footer(text="You have 15 seconds to answer. Type the letter of your answer (A, B, C, D).")
        return quiz_embed

    @staticmethod
    def make_answer_check(ctx: commands.Context):
        def check_answer(message: discord.Message):
            return (
                message.author == ctx.author
                and message.content.lower() in ["a", "b", "c", "d"]
                and message.channel == ctx.message.channel
            )

        return check_answer

    @staticmethod
    def letter_to_index(letter: str) -> int:
        return {"a": 0, "b": 1, "c": 2, "d": 3}[letter.lower()]


# all sorts of classes for playing songs in vc
# you may mostly ignore these since vc implementation is mostly complete.
class VoiceError(Exception):
    pass

class YTDLError(Exception):
    pass

class MixedAudioSource(discord.AudioSource):
    def __init__(self, music_source: discord.AudioSource, *, music_volume_when_tts: float = volume_adjustment, tts_volume_when_mixed: float = tts_volume_adjustment) -> None:
        self.music_source = music_source
        self.tts_source: Optional[discord.AudioSource] = None
        self.music_volume_when_tts = music_volume_when_tts
        self.tts_volume_when_mixed = tts_volume_when_mixed
        self._tts_done: Optional[asyncio.Event] = None

    def start_tts(self, tts_source: discord.AudioSource) -> asyncio.Event:
        self.tts_source = tts_source
        self._tts_done = asyncio.Event()
        return self._tts_done

    def clear_tts(self) -> None:
        self.tts_source = None
        if self._tts_done and not self._tts_done.is_set():
            self._tts_done.set()
        self._tts_done = None

    def is_opus(self) -> bool:
        return False

    def _mix_frames(self, music_frame: bytes, tts_frame: bytes) -> bytes:
        if not music_frame and not tts_frame:
            return b""

        max_len = max(len(music_frame), len(tts_frame))
        if len(music_frame) < max_len:
            music_frame = music_frame.ljust(max_len, b"\x00")
        if len(tts_frame) < max_len:
            tts_frame = tts_frame.ljust(max_len, b"\x00")

        scaled_music = audioop.mul(music_frame, 2, self.music_volume_when_tts)
        scaled_tts = audioop.mul(tts_frame, 2, self.tts_volume_when_mixed)

        mixed = audioop.add(scaled_music, scaled_tts, 2)
        return mixed

    def read(self) -> bytes:
        music_frame = b""
        if self.music_source:
            music_frame = self.music_source.read()

        if not self.tts_source:
            return music_frame

        tts_frame = self.tts_source.read()

        if not tts_frame:
            if self._tts_done and not self._tts_done.is_set():
                self._tts_done.set()
            self.tts_source = None
            self._tts_done = None
            return music_frame

        return self._mix_frames(music_frame, tts_frame)

    def cleanup(self) -> None:
        if self.music_source:
            self.music_source.cleanup()
        if self.tts_source:
            self.tts_source.cleanup()

class YTDLSource(discord.PCMVolumeTransformer):
    YTDLP_COOKIES_BROWSER = 'firefox'
    # change the browser if you want to test,
    # but then change back to firefox once finished testing as that is the browser neel's server relies on.
    # MAKE SURE YOU ARE SIGNED INTO YOUTUBE ON YOUR BROWSER WITH THE ASSOCIATED COOKIES!

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 1.0):
        super().__init__(source, volume)
        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')

    def __str__(self):
        return f'**{self.title}**'

    @classmethod
    async def _extract_info(cls, search: str):
        cmd = [
            'yt-dlp',
            '--dump-single-json',
            '--no-playlist',
            '--default-search', 'auto',
            '--no-check-certificate',
            '--remote-components', 'ejs:github',
            '-f', 'bestaudio[ext=m4a]/bestaudio/best',
            '--cookies-from-browser', cls.YTDLP_COOKIES_BROWSER,
            search,
        ]
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            stderr_str = stderr.decode(errors='replace').strip()
            raise YTDLError(f'Wups! yt-dlp failed: {stderr_str or "unknown error"}')

        stdout_str = stdout.decode(errors='replace').strip()
        if not stdout_str:
            raise YTDLError("Wups! yt-dlp returned no data")

        try:
            return json.loads(stdout_str)
        except json.JSONDecodeError:
            raise YTDLError("Wups! Couldn't parse yt-dlp output")

    @classmethod
    async def create_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        data = await cls._extract_info(search)
        if data is None:
            raise YTDLError(f"Wups! Couldn\'t find anything that matches `{search}`")

        if 'entries' in data:
            info = None
            for entry in data['entries']:
                if entry:
                    info = entry
                    break
        else:
            info = data

        if not info:
            raise YTDLError(f"Wups! Couldn\'t find anything that matches `{search}`")

        return cls(
            ctx,
            discord.FFmpegPCMAudio(
                info['url'],
                before_options='-re -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options='-vn',
            ),
            data=info,
        )

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        parts = [days, hours, minutes, seconds]
        start_idx = None
        for i, part in enumerate(parts):
            if part != 0:
                start_idx = i
                break
        if start_idx is None or start_idx > 2:
            start_idx = 2

        formatted_parts = [f"{part:02d}" for part in parts[start_idx:]]
        return ':'.join(formatted_parts)

class Song:
    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = (discord.Embed(title='Now playing', description=f'**{self.source.title}**', color=discord.Color.purple())
            .add_field( name='Duration', value=self.source.duration)
            .add_field(name='Requested by', value=self.requester.mention)
            .add_field(name='URL', value=f"[Link](<{self.source.url}>)")
            .set_thumbnail(url=self.source.thumbnail))
        return embed
    
class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx
        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()
        self._loop = False
        self._volume = 0.5
        self.skip_votes = set()
        self.mixer = None
        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def loop(self):
        return self._loop

    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def is_playing(self):
        return self.voice and self.current

    async def audio_player_task(self):
        while True:
            self.next.clear()
            try:
                self.current = await self.songs.get()
            except asyncio.CancelledError:
                if self.voice and not self.voice.is_connected():
                    await self.stop()
                return
            except Exception as e:
                print(f"Unexpected error in audio_player_task: {e}")
                await self.stop()
                return

            # ensure current song respects volume
            self.current.source.volume = self._volume

            # create a mixed audio source for this song, allowing tts overlay
            self.mixer = MixedAudioSource(self.current.source, music_volume_when_tts=volume_adjustment)
            self.voice.play(self.mixer, after=self.play_next_song)
            print(f'{Style.BRIGHT}Playing {Fore.MAGENTA}{self.current.source.__str__()[2:-2]}{Fore.RESET} in {Style.RESET_ALL}{Fore.BLUE}{self.voice.channel.name}{Fore.RESET}')
            await self.current.source.channel.send(embed=self.current.create_embed())
            await self.next.wait()

    def play_next_song(self, error=None):
        if error:
            VoiceError(str(error))
        self.next.set()

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing:
            self.voice.stop()

    async def stop(self):
        self.songs.clear()
        if hasattr(self, 'audio_player') and not self.audio_player.done():
            self.audio_player.cancel()
            try:
                await self.audio_player
            except asyncio.CancelledError:
                pass
        if self.voice:
            await self.voice.disconnect()
            self.voice = None


# reusable bot helper functions
# check documentation rentry for more information
def create_list(filename):
    file_checks[filename]=False
    if not os.path.exists(f'csv/{filename}.csv'):
        with open(f'csv/{filename}.csv', 'w'):
            pass # creates csv file
    with open(f'csv/{filename}.csv', mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        rows = list(csv_reader)
        if len(rows)==0:
            file_checks[filename]=True
        else:
            lists[filename]={}
            for row in rows:
                dict = list(row.values())
                lists[filename][dict[0]]=dict[1]

def create_birthday_list():
    if not os.path.exists('csv/birthdays.csv'):
        with open(f'csv/birthdays.csv', 'w'):
            pass # creates csv file
    with open(f'csv/birthdays.csv', mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        rows = list(csv_reader)
        for row in rows:
            user_id = int(row['user_id'])
            birthdate = row['birthdate']
            timezone = row['timezone']
            user_info[user_id] = {'birthdate': birthdate, 'timezone': timezone}

def update_birthday(user_id: int, birthdate: str, tz: str):
    fieldnames = ['user_id', 'birthdate', 'timezone']
    found = False
    rows = []
    with open('csv/birthdays.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(user_id):
                row = {'user_id': row['user_id'], 'birthdate': birthdate, 'timezone': tz}
                found = True
            rows.append(row)
    if not found:
        rows.append({'user_id': str(user_id), 'birthdate': birthdate, 'timezone': tz})
    with open('csv/birthdays.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_birthday_list()

async def check_reaction_board(message, reaction_type):
    emoji, count = None, None

    if reaction_type == "starboard":
        emoji, count = starboard_emoji, starboard_count
    elif reaction_type == "shameboard":
        emoji, count = shame_emoji, starboard_count
    if message.reactions:
        for reaction in message.reactions:
            if str(reaction.emoji) == emoji and reaction.count >= count:
                return True
    return False

async def add_to_board(message, board_type):
    board_name = "hot-seat" if board_type == "starboard" else "cold-seat"
    board_emoji = starboard_emoji if board_type == "starboard" else shame_emoji
    board_text = "⭐" if board_type == "starboard" else "🍅"

    channel = discord.utils.get(message.guild.channels, name=board_name)
    already_on_board = False
    board_msg = None

    async for msg in channel.history():
        if msg.embeds and msg.embeds[0].description == f'[Original Message]({message.jump_url})':
            already_on_board = True
            board_msg = msg
            break

    embed = discord.Embed(color=discord.Color.gold(), description=f'[Original Message]({message.jump_url})')
    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
    embed.set_thumbnail(url=message.author.avatar.url)
    embed.add_field(name='Channel', value=f'<#{message.channel.id}>', inline=True)
    embed.add_field(name='Message', value=f'{str(message.content)}', inline=True)

    if not already_on_board:
        try:
            id = message.author.id
            karma = int(lists["karma"][str(id)])
            if board_name == "hot-seat":
                if karma < 6:
                    add_item("karma", id, 1)
            else:
                if karma > 2:
                    if subtract_item("karma", id, 1):
                        pass
        except:
            pass # probably a bot

    if message.attachments:
        embed.set_image(url=message.attachments[0].url)

    for reaction in message.reactions:
        if str(reaction.emoji) == board_emoji:
            board_reaction = reaction
            embed.set_footer(text=f'{board_reaction.count} {board_text}')
            break

    if already_on_board and board_msg is not None:
        return await board_msg.edit(embed=embed)
    else:
        return await channel.send(embed=embed)

async def reply(ctx, content: str):
    return await ctx.reply(content, mention_author=False)

async def prompt_for_message(bot: commands.Bot, ctx: commands.Context, prompt_text: str, timeout: float, timeout_text: str, timeout_wups: bool = True) -> Optional[tuple[discord.Message, discord.Message]]:
    prompt = await reply(ctx, prompt_text)
    try:
        message = await bot.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=timeout)
    except asyncio.TimeoutError:
        await prompt.delete()
        if timeout_wups:
            await wups(ctx, timeout_text)
        return None
    return prompt, message

def add_coins(userID: int, coins: int):
    fieldnames = ['user_id', 'coins']
    found = False
    rows = []
    with open('csv/coins.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                row = {'user_id': row['user_id'], 'coins': int(row['coins']) + coins}
                found = True
            rows.append(row)
    if not found:
        rows.append({'user_id': str(userID), 'coins': coins})
    with open('csv/coins.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list("coins")

def subtract_coins(userID: int, coins: int) -> bool:
    fieldnames = ['user_id', 'coins']
    found = False
    rows = []
    with open('csv/coins.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                balance = int(row['coins'])
                if balance >= coins:
                    row = {'user_id': row['user_id'], 'coins': balance - coins}
                    found = True
                else:
                    return False
            rows.append(row)
    if not found:
        return False
    with open('csv/coins.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list("coins")
    return True

def dual_spend(userID: int, spending: int) -> bool:
    handBal = int(lists['coins'][str(userID)])
    bankBal = int(lists['bank'][str(userID)])
    totalBal = handBal + bankBal

    if totalBal < spending:
        return False

    spendingLeft = spending

    if handBal < spending:
        if subtract_coins(userID, handBal):
            spendingLeft -= handBal
        if stolen_funds(userID, spendingLeft):
            pass
        return True
    else:
        if subtract_coins(userID, spending):
            return True

def add_item(itemName:str, userID:int, quantity:int):
    fieldnames = ['user_id', f'{itemName}s']
    found = False
    rows = []
    with open(f'csv/{itemName}.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                row = {'user_id': str(userID), f'{itemName}s': int(row[f'{itemName}s']) + quantity}
                found = True
            rows.append(row)
    if not found:
        rows.append({'user_id': str(userID), f'{itemName}s': quantity})
    with open(f'csv/{itemName}.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list(itemName)

def subtract_item(itemName:str, userID:int, quantity:int) -> bool:
    fieldnames = ['user_id', f'{itemName}s']
    found = False
    rows = []
    with open(f'csv/{itemName}.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                balance = int(row[f'{itemName}s'])
                if balance >= quantity:
                    row = {'user_id': row['user_id'], f'{itemName}s': balance - quantity}
                    found = True
                else:
                    return False
            rows.append(row)
    if not found:
        return False
    with open(f'csv/{itemName}.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list(itemName)
    return True

def dep(userID: int, coins: int) -> bool:
    if subtract_coins(userID, coins):
        fieldnames = ['user_id', 'coins']
        found = False
        rows = []
        with open('csv/bank.csv', 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['user_id'] == str(userID):
                    row = {'user_id': row['user_id'], 'coins': int(row['coins']) + coins}
                    found = True
                rows.append(row)
        if not found:
            rows.append({'user_id': str(userID), 'coins': coins})
        with open('csv/bank.csv', 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        create_list("bank")
        return True
    return False

def wd(userID: int, coins: int) -> bool:
    fieldnames = ['user_id', 'coins']
    found = False
    rows = []
    with open('csv/bank.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                if int(row['coins']) >= coins:
                    row = {'user_id': row['user_id'], 'coins': int(row['coins']) - coins}
                    found = True
                else:
                    return False
            rows.append(row)
    if not found:
        return False
    with open('csv/bank.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list("bank")
    add_coins(userID, coins)
    return True

def direct_to_bank(userID: int, coins: int):
    fieldnames = ['user_id', 'coins']
    found = False
    rows = []
    with open('csv/bank.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                row = {'user_id': row['user_id'], 'coins': int(row['coins']) + coins}
                found = True
            rows.append(row)
    if not found:
        rows.append({'user_id': str(userID), 'coins': coins})
    with open('csv/bank.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list("bank")

def stolen_funds(userID: int, coins: int) -> bool:
    fieldnames = ['user_id', 'coins']
    found = False
    rows = []
    with open('csv/bank.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['user_id'] == str(userID):
                balance = int(row['coins'])
                if balance >= coins:
                    row = {'user_id': row['user_id'], 'coins': balance - coins}
                    found = True
                else:
                    return False
            rows.append(row)
    if not found:
        return False
    with open('csv/bank.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    create_list("bank")
    return True

async def in_wom_shenanigans(ctx):
    wom_shenanigans = discord.utils.get(ctx.guild.channels, name='wom-shenanigans')
    if wom_shenanigans is None:
        await shark_react(ctx.message)
        await reply(ctx, "ask for or make a wom-shenanigans channel first, stupid")
        return False
    if not ctx.message.channel.id == wom_shenanigans.id:
        await shark_react(ctx.message)
        await reply(ctx, f"go to <#{wom_shenanigans.id}>, jackass")
        return False
    return True

async def in_channels(ctx, channels: list, giveResponse: bool):
    channelName = ctx.message.channel.name
    ids = []
    for channel in channels:
        ids.append(f"<#{discord.utils.get(ctx.guild.channels, name=channel).id}>")
    if channelName not in channels:
        if giveResponse:
            await shark_react(ctx.message)
            await reply(ctx, f"this command can only be used in the following channels: {", ".join(ids)}. go to one of those channels, jackass")
        return False
    return True

async def in_threads(ctx, threads: list, giveResponse: bool):
    threadName = ctx.message.channel.name
    ids = []
    for thread in threads:
        ids.append(f"<#{discord.utils.get(ctx.guild.threads, name=thread).id}>")
    if threadName not in threads:
        if giveResponse:
            await shark_react(ctx.message)
            await reply(ctx, f"this command can only be used in the following threads: {", ".join(ids)}. go to one of those channels, jackass")
        return False
    return True

def assert_cooldown(command, user_id):
    global last_executed

    def cleanup_old_cooldowns(command):
        global last_executed
        current_time = time.time()
        to_remove = [user_id for user_id, timestamp in last_executed[command].items() 
                    if current_time - timestamp > 3600]
        for user_id in to_remove:
            del last_executed[command][user_id]

    if random.randint(1, 100) == 1:
        cleanup_old_cooldowns(command)
    if user_id not in last_executed[command] or last_executed[command][user_id] + cooldowns[command] < time.time():
        last_executed[command][user_id] = time.time()
        return 0
    return round(last_executed[command][user_id] + cooldowns[command] - time.time())

def cooldown_remaining(command, user_id) -> int:
    if command not in cooldowns or command not in last_executed:
        return 0

    current_time = time.time()
    last_time = last_executed[command].get(user_id)
    if last_time is None:
        return 0

    # clean up old cooldowns
    if current_time - last_time > 3600:
        return 0

    remaining = last_time + cooldowns[command] - current_time
    return max(0, round(remaining))

def capitalize_string(string: str) -> str:
    return ' '.join(word.capitalize() for word in string.split('-'))

async def shark_react(message: discord.Message):
    return await message.add_reaction('🦈')

async def wups(ctx, content: str):
    await shark_react(ctx.message)
    return await reply(ctx, content=f"Wups! {content}...")

def load_info(info: str):
    file_path = os.path.join(os.path.dirname(__file__), "docs", f"{info}.txt")
    with open(file_path, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]
