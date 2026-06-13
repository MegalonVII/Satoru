import discord

from discord.ext import commands
from datetime import datetime

from utils import *

# birthday commands start here
# birthday, bdl
class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='birthday')
    async def birthday(self, ctx):
        if await in_wom_shenanigans(ctx):
            bday, tz_obj, err = await collect_birthday_and_timezone(self.bot, ctx)
            if err:
                return await wups(ctx, err)
            return await reply(ctx, f'Birthday set for {bday} in {tz_obj}!')
            
    @commands.command(name='birthdaylist', aliases=['bdaylist', 'bdl'])
    async def birthday_list(self, ctx):
        if await in_wom_shenanigans(ctx):
            temp_data = []
            for key in user_info.keys():
                member = discord.utils.get(ctx.message.guild.members, id=key)
                temp_data.append({'user': member, 'birthday': datetime.strptime(user_info[key]['birthdate'], '%m-%d').date().strftime('%B %d')})
            temp_data = sorted(temp_data, key=lambda x: datetime.strptime(x['birthday'], '%B %d').date())
            embed = discord.Embed(title='Marina Birthdays', color=discord.Color.blue())
            desc = ''
            for data in temp_data:
                desc += f'{data['user'].mention}: **{data['birthday']}**\n\n'
            embed.description = desc
            embed.set_thumbnail(url=self.bot.guilds[0].icon.url)
            return await ctx.reply(embed=embed, mention_author=False)
        

async def setup(bot):
    await bot.add_cog(Birthday(bot))
