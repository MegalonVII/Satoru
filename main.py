import discord
import logging

from discord.ext import commands
from os import getenv
from dotenv import load_dotenv
from sys import exit
from datetime import datetime

from utils import *

# token instantiation
load_dotenv()
TOKEN=getenv('DISCORD_TOKEN')

# bot initialization
bot=commands.Bot(command_prefix = '!w ', intents=discord.Intents.all())
bot.remove_command('help')
extensions=['fun', 'economy', 'admin', 'flair', 'misc', 'birthday', 'music', 'events']

HELP_TITLES = {
    "home": "Need help?",
    "fun": "Fun Commands",
    "economy": "Economical Commands",
    "admin": "Administrative Commands",
    "flair": "Flair Commands",
    "birthday": "Birthday Commands",
    "music": "Musical Commands",
    "misc": "Miscellaneous Commands",
}

HELP_DATA = load_help()

# bot forced to use in server
@bot.check
async def cog_check(ctx):
    return bool(ctx.guild)

# bot help command
@bot.command(name='help')
async def help(ctx, page: str = "home"):
    page = page.lower()

    if page not in HELP_DATA:
        options = ", ".join(f"`{key}`" for key in HELP_DATA.keys() if key != "home")
        return await wups(ctx, f'Invalid page name. Try one of: {options}')

    embed = discord.Embed(color=discord.Color.purple())
    embed.title = HELP_TITLES.get(page, f"{page.capitalize()} Commands")

    commands_list = HELP_DATA[page]["commands"]
    descriptions_list = HELP_DATA[page]["descriptions"]

    for name, value in zip(commands_list, descriptions_list):
        embed.add_field(name=name, value=value, inline=False)

    if page != "home":
        embed.set_footer(text=f'Viewing page: {page}')
    
    embed.set_thumbnail(url=bot.user.avatar.url)
    return await ctx.reply(embed=embed, mention_author=False)

# on_ready
@bot.event
async def on_ready():
    for file in files: # creates all lists wom stores
        create_list(file)
    create_birthday_list()
      
    try:
        for extension in extensions: # loads extensions for other commands
            await bot.load_extension(f'exts.{extension}')
    except Exception as e:
        print(e)
        exit(1)

    for member in bot.guilds[0].members: # mandates user has karma for roulette, along with other information
        if not member.bot:
            id_str = str(member.id)
            id = member.id
            if not id_str in lists["karma"].keys():
                add_item("karma", id, 2)
            if not id_str in lists["coins"].keys():
                add_coins(id, 100)
            if not id_str in lists["bank"].keys():
                direct_to_bank(id, 0)

    __import__("utils").starttime = datetime.now(timezone(login_timezone))

    return print(f"Logged in as: {bot.user.name}\nID: {bot.user.id}\n" + get_login_time(login_timezone)) # fully logged in with everything loaded in the backend

# everything has finally been set up
# we can now run the bot
async def main():
    await bot.start(TOKEN)

try:
    asyncio.run(main())
except:
    pass
