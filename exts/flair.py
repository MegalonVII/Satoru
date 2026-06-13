import discord
import csv
import pandas as pd

from discord.ext import commands
from asyncio import sleep

from utils import *

# flair commands start here
# addf, delf, lf, im
class Flair(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='addflair', aliases=['addf'])
    async def addflair(self, ctx, role: discord.Role):
        try:
            if not ctx.author.guild_permissions.administrator:
                return await wups(ctx, 'Only administrators can use this command')
            if role.position >= ctx.me.top_role.position:
                return await wups(ctx, "I can't add this role as a flair because it is above my highest role")
            if role.name in lists["flairs"].keys():
                return await wups(ctx, f"'{role.name}' is already a flair")
            
            with open('csv/flairs.csv', 'a', newline='') as csvfile:
                fieldnames = ['role_name', 'role_id']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames) 
                if file_checks["flairs"]:
                    writer.writeheader()
                writer.writerow({'role_name': role.name, 'role_id': role.id})
            create_list("flairs")
            await ctx.message.add_reaction('✅')
            await sleep(3)
            return await ctx.message.delete()
        except:
            return await wups(ctx, 'Something went wrong. Try doing `!w addflair @Role`')

    @commands.command(name='deleteflair', aliases=['delf'])
    async def deleteflair(self, ctx, role:discord.Role):
        if not ctx.author.guild_permissions.administrator:
            return await wups(ctx, 'You do not have the required permissions')
        if not role.name in list(lists["flairs"].keys()):
            return await wups(ctx, 'This role is not a flair')
        if len(list(lists["flairs"].keys())) == 0:
            return await wups(ctx, 'There are no flairs to delete in the first place')
        
        flairs = pd.read_csv('csv/flairs.csv')
        flairs = flairs[flairs.role_name != role.name]
        flairs.to_csv('csv/flairs.csv', index=False)
        create_list("flairs")
        await ctx.message.add_reaction('✅')
        await sleep(3)
        return await ctx.message.delete()

    @commands.command(name='listflairs', aliases=['lf'])
    async def listflairs(self, ctx):
        try:
            await ctx.send('\n'.join(list(lists["flairs"].keys())))
            return await ctx.message.delete()
        except:
            return await wups(ctx, 'There are no self-assignable roles in this server')

    @commands.command(name='im')
    async def im(self, ctx, *roleName:str):
        if await in_wom_shenanigans(ctx):
            roleName = ' '.join(roleName) # finds the role from the name given
            role = discord.utils.get(ctx.guild.roles, name=roleName)
            if role is None:
                return await wups(ctx, "Invalid role")
            if role.name not in list(lists["flairs"].keys()): # checks if it is a flair
                return await wups(ctx, "That is not a self-assignable role")
            
            hasRole = False # checks if the user already has the role
            for userRole in ctx.author.roles:
                if userRole.id == role.id:
                    hasRole = True
                    break
                
            if hasRole: # gives or removes role
                await ctx.author.remove_roles(role)
            else:
                await ctx.author.add_roles(role)
            await ctx.message.add_reaction('✅')
            await sleep(3)
            return await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(Flair(bot))
