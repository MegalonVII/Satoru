import discord

from discord.ext import commands
from asyncio import subprocess, create_subprocess_shell
from datetime import datetime

from utils import *

# misc commands start here
# ping, whomuted, avi, emote, convert, translate
class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conversions = {
            ("c", "f"): lambda x: x * 9/5 + 32,
            ("f", "c"): lambda x: (x - 32) * 5/9,
            ("m", "ft"): lambda x: x * 3.28084,
            ("ft", "m"): lambda x: x * 0.3048,
            ("kg", "lb"): lambda x: x * 2.20462,
            ("lb", "kg"): lambda x: x * 0.453592,
            ("mi", "km"): lambda x: x * 1.60934,
            ("km", "mi"): lambda x: x * 0.621371,
            ("in", "cm"): lambda x: x * 2.54,
            ("cm", "in"): lambda x: x * 0.393701
        }
        self.currencies = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CAD": "CA$",
            "PHP": "₱",
            "MXN": "MX$"
        }

    @commands.command(name='ping')
    async def ping(self, ctx):
        await ctx.message.delete()

        for file in files:
            create_list(file)
        create_birthday_list()

        return await ctx.send(f'Pong! {round (self.bot.latency * 1000)}ms')
    
    @commands.command(name='whomuted')
    async def whomuted(self, ctx):
        try:
            return await reply(ctx, ", ".join([member.name for member in ctx.guild.members if member.is_timed_out()]))
        except:
            return await wups(ctx, "No one is muted currently", mention_author=False)
    
    @commands.command(name='avatar', aliases=['avi'])
    async def avatar(self, ctx, member:discord.Member=None):
        member = member or ctx.author
        e = discord.Embed(title=f"{member.name}'s Avatar", color=discord.Color.purple())
        if member.display_avatar.url != member.avatar.url:
            e.set_thumbnail(url=member.avatar.url)
        e.set_image(url=member.display_avatar.url)
        e.set_footer(text=f"Requested by: {ctx.message.author.name}") if member is not ctx.author else None
        return await ctx.reply(embed=e, mention_author=False)
    
    @commands.command(name='emote')
    async def emote(self, ctx, emote:discord.Emoji):
        embed = discord.Embed(color=discord.Color.purple())
        embed.description=f"**__Emote Information__**\n**URL**: {emote.url}\n**Name**: {emote.name}\n**ID**: {emote.id}"
        embed.set_image(url=emote.url)
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name='convert')
    async def convert(self, ctx, value: float, org_unit: str, new_unit: str):
        org_unit = org_unit.lower()
        new_unit = new_unit.lower()
        unit_mapping = {"f": "F", "c": "C"}

        if (org_unit, new_unit) in self.conversions:
            result = self.conversions[(org_unit, new_unit)](value)
            org_unit = unit_mapping.get(org_unit, org_unit)
            new_unit = unit_mapping.get(new_unit, new_unit)
            return await reply(ctx, f"{value} {org_unit} is equal to {result:.2f} {new_unit}.")
        else:
            return await wups(ctx, "Invalid conversion")
            
    @commands.command(name='translate')
    async def translate(self, ctx, *, phrase):
        async with ctx.typing():
            process = await create_subprocess_shell(f'trans -b :en "{phrase}"', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await process.communicate()
            if stderr:
                return await wups(ctx, f"A translation error occurred. ({stderr.decode().strip()})")
            return await reply(ctx, f"Translated: {stdout.decode().strip()}\n\n*Beware of some inaccuracies. I cannot be 100% accurate...*")
    
    @commands.command(name='uptime')
    async def uptime(self, ctx):
        if await in_wom_shenanigans(ctx):
            try:
                await ctx.message.delete()
            except Exception:
                pass

            if ctx.author.id == 347503746835546134 or "wom coder" in [role.name for role in ctx.author.roles] : # neel user id
                return await ctx.send(f"Uptime: {get_uptime_text()}", delete_after=5)
            else:
                return await ctx.send("Wups! You are not authorized to use this command...", delete_after=5)

    @commands.command(name='currency')
    async def currency(self, ctx, amount: float, from_curr: str, to_curr: str):
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        for code in (from_curr, to_curr):
            if code not in self.currencies:
                supported = ", ".join(self.currencies.keys())
                return await wups(ctx, f"{code} isn't supported. Available: `{supported}`")

        if from_curr == to_curr:
            return await wups(ctx, "I cannot convert a currency to itself")

        rate = await get_rate(ctx, from_curr, to_curr)
        if rate is None:
            return await wups(ctx, "Could not fetch exchange rates. Try again later")

        converted = amount * rate
        from_sym = self.currencies[from_curr]
        to_sym = self.currencies[to_curr]

        return await reply(ctx, f"{from_sym}{amount:,.2f} {from_curr} is equal to {to_sym}{converted:,.2f} {to_curr}\n-# Rate: 1 {from_curr} = {to_sym}{rate:,.4f} {to_curr}")

async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
