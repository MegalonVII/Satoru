import discord
import random

from discord.ext import commands
from asyncio import sleep
from math import ceil

from utils import *

# economy commands
# slots, bet, steal, heist, dep, wd, bal, bankbal, paypal, mp, buy, sell, inv, use
class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.info = ['items', 'priceStrs', 'descs']
        for item in self.info:
            setattr(self, item, load_info(item))
        self.prices = [int(s.replace(',', '')) for s in self.priceStrs]
  
    @commands.command(name='slots')
    async def slots(self, ctx):
        if await in_heaven(ctx):
            if assert_cooldown('slots', ctx.author.id) != 0:
                return await error(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('slots', ctx.author.id)} seconds")
            if not subtract_coins(ctx.author.id, 10):
                return await error(ctx, f"You don't have enough {gojo_washington_word()} to play")
        
            emojis = ["🍒", "🍇", "🍊", "🍋", "🍉", "🫐", "7️⃣"]
            reels = ["❓"] * 3
            msg = await ctx.reply(f"{reels[0]} | {reels[1]} | {reels[2]}", mention_author=False)

            for i in range(3):
                await sleep(1)
                reels[i] = random.choice(emojis)
                await msg.edit(content=f"{reels[0]} | {reels[1]} | {reels[2]}", allowed_mentions=discord.AllowedMentions.none())

            return await msg.edit(content=slots_tally_and_payout(ctx.author.id, reels), allowed_mentions=discord.AllowedMentions.none())

    @commands.command(name='bet')
    async def bet(self, ctx, amount:int):
        if await in_heaven(ctx):
            if assert_cooldown('bet', ctx.author.id) != 0:
                return await error(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('bet', ctx.author.id)} seconds")
            if subtract_coins(ctx.author.id, amount):
                roll = random.randint(1,6)
                roll2 = random.randint(1,6)
                result = roll + roll2
                if result == 7:
                    add_coins(ctx.author.id, 2*amount)
                    return await reply(ctx, f"You rolled a {result}! You win!")
                return await reply(ctx, f"You rolled a {result}! Sorry, you lost...")
            return await error(ctx, f"You can't bet that much {gojo_washington_word()} as you don't have that much")

    @commands.command(name='steal')
    async def steal(self, ctx, target: discord.Member):
        if await in_heaven(ctx):
            if target.bot or target == ctx.author:
                return await error(ctx, "You can't steal from a bot or from yourself")
            if not steal_target_tracking(ctx.author.id, target, update_counts=False):
                return await error(ctx, "You can't target this person again so soon. Choose a different target")
            if assert_cooldown('steal', ctx.author.id) != 0:
                return await error(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('steal', ctx.author.id)} seconds")

            # tracks if someone is specifiically targetting another person
            steal_target_tracking(ctx.author.id, target, update_counts=True)

            if random.randint(1, 10) <= 5:
                random_steal = random.randint(1, 100)
                if subtract_coins(target.id, random_steal):
                    add_coins(ctx.author.id, random_steal) # successful steal
                    return await reply(ctx, f"You successfully stole {random_steal} {gojo_washington_word(random_steal)} {gojowashington} from {target.name}!")
                return await reply(ctx, f"You tried stealing {random_steal} {gojo_washington_word(random_steal)} {gojowashington} from {target.name}, but they don't have enough {gojo_washington_word()} on hand...") # successful steal, but couldn't do it

            lost_coins = random.randint(1, 100)
            if dual_spend(ctx.author.id, lost_coins): # unsuccessful steal
                add_coins(target.id, lost_coins)
                return await reply(ctx, f"You got caught trying to steal {lost_coins} {gojo_washington_word(lost_coins)} {gojowashington} from {target.name}! You were forced to pay them back instead...")
            return await reply(ctx, f"You got caught trying to steal {lost_coins} {gojo_washington_word(lost_coins)} {gojowashington} from {target.name}! However, you weren't able to pay them back...") # successful steal, couldn't pay back

    @commands.command(name='heist')
    async def heist(self, ctx):
        if await in_heaven(ctx):
            if assert_cooldown("heist", ctx.author.id) != 0:
                return await error(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('heist', ctx.author.id)} seconds")
            if random.randint(1, 100) == 1: # successful heist
                total = 0
                for key in lists['bank'].keys():
                    amount = int(lists['bank'][key])
                    if stolen_funds(int(key), amount):
                        total += amount
                        add_coins(ctx.author.id, amount)
                return await reply(ctx, f"Successful heist! {total} {gojo_washington_word(total)} {gojowashington}!")
            else: # unsuccesful heist
                bailAmt = (int(lists['coins'][str(ctx.author.id)]) + int(lists['bank'][str(ctx.author.id)])) // 5

                if bailAmt == 0: # total balance less than 5
                    subtract_coins(ctx.author.id, int(lists['coins'][str(ctx.author.id)]))
                    stolen_funds(ctx.author.id, int(lists['bank'][str(ctx.author.id)]))
                    return await reply(ctx, "Unsuccessful heist! <:PoM:888677251615449158> arrested you! You couldn't pay a bail, however, so you paid what little you had left and wrote an IOU...") # unsuccessful, clears out what little you have, brokie

                if dual_spend(ctx.author.id, bailAmt):
                    return await reply(ctx, f"Unsuccessful heist! <:PoM:888677251615449158> arrested you! You paid {bailAmt} {gojo_washington_word(bailAmt)} {gojowashington} as bail...") # unsuccessful, pays 20% of total balance

    @commands.command(name='deposit', aliases=['dep'])
    async def deposit(self, ctx, amt:int):
        if await in_heaven(ctx):
            if dep(ctx.author.id, amt):
                return await reply(ctx, f"Successfully deposited {amt} {gojo_washington_word(amt)} {gojowashington}!")
            return await error(ctx, "Insufficient funds")

    @commands.command(name='withdraw', aliases=['wd'])
    async def withdraw(self, ctx, amt:int):
        if await in_heaven(ctx):
            if wd(ctx.author.id, amt):
                return await reply(ctx, f"Successfully withdrew {amt} {gojo_washington_word(amt)} {gojowashington}!")
            return await error(ctx, "Insufficient funds")

    @commands.command(name='balance', aliases=['bal'])
    async def balance(self, ctx, member:discord.Member = None):
        member = member or ctx.author
        if not member == ctx.author:
            if subtract_coins(ctx.author.id, 10):
                add_coins(member.id, 10)
            else:
                return await error(ctx, "Insufficient funds")
        for userID in lists['coins'].keys():
            if str(member.id) == userID:
                balance = int(lists['coins'][str(member.id)])
                if not member == ctx.author:
                    return await reply(ctx, f"{member.name} has {balance} {gojo_washington_word(balance)} {gojowashington}!")
                return await reply(ctx, f"You have {balance} {gojo_washington_word(balance)} {gojowashington}!")
        return await error(ctx, "Get some bread, broke ass")

    @commands.command(name='bankbalance', aliases=['bankbal'])
    async def bankbalance(self, ctx):
        for userID in lists['bank'].keys():
            if str(ctx.author.id) == userID:
                balance = int(lists['bank'][str(ctx.author.id)])
                return await reply(ctx, f"You have {balance} {gojo_washington_word(balance)} {gojowashington} in the bank!")
        return await error(ctx, "Get some bread, broke ass")

    @commands.command(name='paypal')
    async def paypal(self, ctx, recipient:discord.Member, amount:int):
        if await in_heaven(ctx):
            if amount <= 0:
                return await error(ctx, "Invalid payment amount")
            if recipient.bot or recipient.id == ctx.author.id:
                return await error(ctx, "You can't pay a bot or yourself")
            if subtract_coins(ctx.author.id,amount):
                add_coins(recipient.id,amount)
                return await reply(ctx, f"{recipient.name} has received {amount} {gojo_washington_word(amount)} {gojowashington} from you!")
            return await error(ctx, f"You don't have that much {gojo_washington_word()}")

    @commands.command(name='marketplace', aliases=['mp'])
    async def marketplace(self, ctx):
        embed = discord.Embed(title='Marketplace', color=discord.Color.green())
        for i in range(0, len(self.items)):
            price = int(self.priceStrs[i].replace(',', ''))
            embed.add_field(name=f'{self.items[i]}, {self.priceStrs[i]} {gojo_washington_word(price)} {gojowashington}', value=f'{self.descs[i]}', inline=False)
        embed.set_footer(text='If you want to purchase any of these items, use .gojo buy (item name). The item name is exactly as you see it in this marketplace!')
        return await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name='buy')
    async def buy(self, ctx, item:str, number:int = 1):
        if await in_heaven(ctx):
            if number < 1:
                return await error(ctx, "Invalid number requested")
            item = item.lower()
            for item_name, item_price in zip(self.items, self.prices):
                if item.lower() == item_name:
                    if not subtract_coins(ctx.author.id, number * item_price):
                        return await error(ctx, f"You don't have enough {gojo_washington_word()}")
                    add_item(item, ctx.author.id, number)
                    return await reply(ctx, f"You have successfully purchased {number} {item_name}{"s" if number > 1 else ""}!")
            return await error(ctx, "Invalid item")

    @commands.command(name='sell')
    async def sell(self, ctx, item:str, number:int = 1):
        if await in_heaven(ctx):
            if number < 1:
                return await error(ctx, "Invalid number requested")
            item = item.lower()
            for name, price in zip(self.items, self.prices):
                sell = price // 2
                if item == name:
                    if subtract_item(item, ctx.author.id, number):
                        add_coins(ctx.author.id, number * sell)
                        payout = number * sell
                        if number == 1:
                            return await reply(ctx, f'Successfully sold {number} {item}! {payout} {gojo_washington_word(payout)} {gojowashington}!')
                        else:
                            return await reply(ctx, f'Successfully sold {number} {item}s! {payout} {gojo_washington_word(payout)} {gojowashington}!')
                    return await error(ctx, f"You don't have that many {item}s") 
            return await error(ctx, "Invalid item")
  
    @commands.command(name='inventory', aliases=['inv'])
    async def inventory(self, ctx):
        if await in_heaven(ctx):
            inventorySTR = "You have...\n\n"
            async with ctx.typing():
                for item in self.items:
                    inventorySTR += f'{int(lists[item].get(str(ctx.author.id), 0))} {item}s\n'
            return await reply(ctx, inventorySTR)

    @commands.command(name='use')
    async def use(self, ctx, item:str):
        if await in_heaven(ctx):
            item = item.lower()
            if item not in self.items:
                return await error(ctx, "Invalid item")
            return await EconomyUseHandlers.handle(self.bot, ctx, item)

async def setup(bot):
    await bot.add_cog(Economy(bot))
