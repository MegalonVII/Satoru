import discord
import random
import asyncio
import requests
import json
import urllib.parse
import pypokedex as dex

from discord.ext import commands
from datetime import timedelta

from utils import *

# fun commands start here
# say, custc, snipe, esnipe, choose, pokedex, who, howgay, rps, 8ball, roulette, trivia, emulation, deathbattle, ship
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.info = ["actions", "deaths", "survivals", "shipNotes"]
        for item in self.info:
            setattr(self, item, load_info(item))
        self.consoles = load_emulation()
        self.currentFight = False

    @commands.command(name='say')
    async def say(self, ctx, *args):
        try:
            await ctx.message.delete()
            return await ctx.channel.send(" ".join(args).replace('"', '\"').replace("'", "\'"), allowed_mentions=discord.AllowedMentions(everyone=False, roles=False))
        except:
            return await wups(ctx, "You need something for me to say")
                
    @commands.command(name='customcommands', aliases=['custc'])
    async def customcommands(self, ctx):
        try:
            return await reply(ctx, ', '.join(list(lists["commands"].keys())))
        except:
            return await wups(ctx, 'There are no custom commands')

    @commands.command(name='snipe')
    async def snipe(self, ctx):
        channel = ctx.channel
        try:
            data = snipe_data[channel.id]
            if data["attachment"] and 'video' in data["attachment"].content_type:
                data["content"] += f"\n[Attached Video]({data['attachment'].url})"
            embed = discord.Embed(title=f"Last deleted message in #{channel.name}", color = discord.Color.purple(), description=str(data["content"]))
            if data["attachment"] and 'image' in data["attachment"].content_type:
                embed.set_image(url=data["attachment"].url)
            embed.set_footer(text=f"This message was sent by {data['author']}")
            embed.set_thumbnail(url=data['author'].avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)
        except KeyError:
            return await wups(ctx, f"There are no recently deleted messages in <#{channel.id}>")

    @commands.command(name='editsnipe', aliases=['esnipe'])
    async def editsnipe(self, ctx):
        channel = ctx.channel
        try:
            data = editsnipe_data[channel.id]
            embed = discord.Embed(title=f"Last edited message in #{channel.name}", color = discord.Color.purple(), description=str(data["content"]))
            embed.set_footer(text=f"This message was sent by {data['author']}")
            embed.set_thumbnail(url=data["author"].avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)
        except KeyError:
            return await wups(ctx, f"There are no recently edited messages in <#{channel.id}>")

    @commands.command(name='choose')
    async def choose(self, ctx, *args):
        if (len(args) < 2):
            return await wups(ctx, "You need at least 2 arguments for me to choose from")
        return await reply(ctx, f"I choose `{random.choice(args)}`!")

    @commands.command(name='pokedex')
    async def pokedex(self, ctx, index: int):
        if index > 1017 or index < 1:
            return await wups(ctx, "Invalid index")
          
        async with ctx.typing():
            # data collections
            pokemon = dex.get(dex=index)
            res = requests.get(f'https://pokeapi.co/api/v2/pokemon-species/{index}')
            encRes = requests.get(f'https://pokeapi.co/api/v2/pokemon/{index}/encounters')
            pokRes = requests.get(f'https://pokeapi.co/api/v2/pokemon/{index}/')
            data = res.json()
            encData = encRes.json()
            pokData = pokRes.json()

            shinyInt = random.randint(1, 512)
            embed, shiny = build_pokedex_embed(pokemon, data, encData, pokData, index, shinyInt)
            if shiny:
                return await ctx.reply(content=shiny_content, embed=embed, mention_author=False)
            return await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name='who')
    async def who(self, ctx):
        return await reply(ctx, f"`{ctx.message.content[3:]}`? {random.choice([member.display_name for member in ctx.message.guild.members if not member.bot])}")
        
    @commands.command(name='howgay')
    async def howgay(self, ctx, member:discord.Member=None):
        if assert_cooldown("howgay", ctx.author.id) != 0:
            return await wups(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('howgay', ctx.author.id)} seconds")
    
        member = member or ctx.author
        percent = random.randint(0,100)
        responses = ['You\'re not into that mentally ill crap.', 'You\'re probably just going through a phase...', 'It\'s ok to be gay, buddy. We\'ll support you... unless you make it your entire personality.', 'You **LOVE** it up the rear end, don\'t you?']
        if percent >= 0 and percent <= 25:
            response = responses[0]
        elif percent >= 26 and percent <= 50:
            response = responses[1]
        elif percent >= 51 and percent <= 75:
            response = responses[2]
        elif percent >= 76 and percent <= 100:
            response = responses[3]
        
        return await reply(ctx, f"{member.name} is {percent}% gay. {response}")

    @commands.command(name='rps')
    async def rps(self, ctx, playerChoice: str=None):
        if await in_wom_shenanigans(ctx):
            if assert_cooldown("rps", ctx.author.id) != 0 :
                return await wups(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('rps', ctx.author.id)} seconds")
            if playerChoice is None:
                return await wups(ctx, "You need to give me your choice")
            
            playerChoice = playerChoice.lower()
            choices = ['rock', 'paper', 'scissors']
            if playerChoice not in choices:
                return await wups(ctx, "Invalid choice")
            else:
                botChoice = random.choice(choices)
                if playerChoice == botChoice: # both tie
                    return await reply(ctx, f"I chose `{botChoice}`.\nUgh! Boring! We tied...")
                elif (playerChoice == choices[0] and botChoice == choices[1]) or \
                    (playerChoice == choices[1] and botChoice == choices[2]) or \
                    (playerChoice == choices[2] and botChoice == choices[0]): # bot wins
                        return await reply(ctx, f"I chose `{botChoice}`.\nHah! I win, sucker! Why'd you pick that one, stupid?")
                else: # bot loses
                    return await reply(ctx, f"I chose `{botChoice}`.\nWell played there. You have bested me...")

    @commands.command(name='8ball')
    async def eightball(self, ctx):
        if assert_cooldown("8ball", ctx.author.id) != 0 :
            return await wups(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('8ball', ctx.author.id)} seconds")
        if len(ctx.message.content) < 9:
            return await wups(ctx, "You need to give me a question to respond to")
        
        responses = ['Hell yeah!', 'It is certain.', 'Without a doubt.', 'You may rely on it.', 'Yes, definitely.', 'It is decidedly so.', 'As I see it, yes.', 'Most likely.', 'Yes.', 'Outlook good.', 'Signs point to yes.', 'You already know the answer.', 'Reply hazy, try again.', 'Better not tell you now.', 'Ask again later.', 'Cannot predict now.', 'Concentrate and ask again.', 'Don\'t count on it.', 'Outlook not so good.', 'My sources say no.', 'Very doubtful.', 'My reply is no.', 'No.', 'Oh god, no.']
        return await reply(ctx, f"🎱 `{ctx.message.content[9:]}` 🎱\n{random.choice(responses)}")

    @commands.command(name='roulette')
    async def roulette(self, ctx, member:discord.Member=None):
        if assert_cooldown("roulette", ctx.author.id) != 0:
            return await wups(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('roulette', ctx.author.id)} seconds")

        target = member or ctx.author
        if target.bot:
            return await wups(ctx, "❌🔫 You can\'t shoot the one with the bullets")

        chance = int(lists["karma"][str(target.id)])
        is_self = target == ctx.author

        if is_self:
            if target.guild_permissions.administrator:
                return await wups(ctx, "❌🔫 Looks like you\'re safe, you filthy admin...")
            return await roulette_spin(ctx, target, True, chance)

        if not ctx.author.guild_permissions.administrator:
            return await wups(ctx, "❌🔫 A lowlife like you can\'t possibly fire the gun at someone else...")
        if target.guild_permissions.administrator:
            return await wups(ctx, "❌🔫 Looks like they\'re safe, that filthy admin...")
        if target.is_timed_out():
            return await wups(ctx, "❌🔫 Don\'t you think it\'d be overkill to shoot a dead body?")

        return await roulette_spin(ctx, target, False, chance)

    @commands.command(name='trivia')
    async def trivia(self, ctx, type:str = None):
        if await in_wom_shenanigans(ctx):
            if assert_cooldown("trivia", ctx.author.id) != 0:
                return await wups(ctx, f"Slow down there, bub! Command on cooldown for another {cooldown_remaining('trivia', ctx.author.id)} seconds")

            category_id, err = TriviaHandlers.resolve_trivia_category(type)
            if err:
                return await wups(ctx, err)
            if category_id is None:
                return await wups(ctx, "Invalid trivia type")

            async with ctx.typing():
                question, correct_answer, options = TriviaHandlers.fetch_trivia(category_id)

            await ctx.reply(embed=TriviaHandlers.build_trivia_embed(question, options), mention_author=False)

            try:
                answer_message = await ctx.bot.wait_for("message", timeout=15.0, check=TriviaHandlers.make_answer_check(ctx))
            except asyncio.TimeoutError:
                return await reply(ctx, f"Time's up! The correct answer was **{correct_answer}**.")

            selected_answer = options[TriviaHandlers.letter_to_index(answer_message.content)]

            if selected_answer == correct_answer:
                add_coins(ctx.author.id, 10)
                return await answer_message.reply(f"Correct! The answer is **{correct_answer}**. 10 {zenny}!", mention_author=False)

            return await answer_message.reply(f"Sorry, that's incorrect. The correct answer is **{correct_answer}**.", mention_author=False)
            
    @commands.command(name='emulation')
    async def emulation(self, ctx, console: str = "guide"):
        if await in_channels(ctx, ["gamig", "gamig-2-coming-soon", "wom-shenanigans"], False) or await in_threads(ctx, ['Rip-bozotendo'], False):
            if console == "guide":
                return await reply(ctx, "# __Emulation Wiki__\n\n## This is a wiki on how to get emulators for various systems set up on a PC!\n\n__**List of Valid Consoles**__ (enter as `!w emulation (console name)`)\n- NES\n- SNES\n- N64\n- GameCube\n- Wii\n- Wii U (enter as \"WiiU\")\n- GameBoy (enter as \"GB\")\n- GameBoy Color (enter as \"GBC\")\n- GameBoy Advance (enter as \"GBA\")\n- DS\n- 3DS\n- Switch\n- PS1\n- PS2\n- PS3\n- PSP\n- PS Vita (enter as \"PSVita\")\n- Master System (enter as \"MasterSystem\")\n- Genesis\n- Saturn\n- Dreamcast\n- Xbox")
            elif console.lower() not in self.consoles.keys():
                return await wups(ctx, "You entered a console that isn't on the list of valid consoles. Please refer to the list by entering `!w emulation`")

            for key, value in self.consoles.items():
                if console.lower() == key:
                    return await reply(ctx, f"# {", ".join(value['links'])}\n{value['instructions']}\n\n*Go hog wild.*")
        else:
            ids = []
            for channel in ["gamig", "gamig-2-coming-soon", "wom-shenanigans"]:
                ids.append(f"<#{discord.utils.get(ctx.guild.channels, name=channel).id}>")
            ids.append(f"<#{discord.utils.get(ctx.guild.threads, name="Rip-bozotendo").id}>")
            await shark_react(ctx.message)
            return await reply(ctx, f"this command can only be used in the following channels: {", ".join(ids)}. go to one of those channels, jackass")

    @commands.command(name='deathbattle', aliases=['db'])
    async def deathbattle(self, ctx, member: discord.Member):
        if await in_wom_shenanigans(ctx):
            if self.currentFight:
                return await wups(ctx, f"There is currently a fight going on")
            if member.bot:
                return await wups(ctx, f"You can't fight a bot")

            self.currentFight = True
            actor, target = (ctx.author, member) if random.choice([True, False]) else (member, ctx.author); msg = await reply(ctx, f"{ctx.author.name} challenges {member.name} to the death!")
            await asyncio.sleep(3)
            while True:
                choiceNum = random.randint(0, len(self.actions) - 1)
                await msg.edit(content=self.actions[choiceNum].format(actor.name, target.name), allowed_mentions=discord.AllowedMentions.none())
                await asyncio.sleep(2)
                determinant = random.randint(1, int(lists["karma"][str(target.id)]))
                response = self.actions[choiceNum] + f" {self.deaths[choiceNum]}" if determinant == 1 else self.actions[choiceNum] + f" {self.survivals[choiceNum]}"
                await msg.edit(content=response.format(actor.name, target.name, target.name), allowed_mentions=discord.AllowedMentions.none())
                if determinant == 1:
                    self.currentFight = False
                    break
                actor, target = target, actor
                await asyncio.sleep(3)

    @commands.command(name='ship')
    async def ship(self, ctx: commands.Context, str1: str, str2: str):
        if await in_wom_shenanigans(ctx):
            half_str1 = str1[:len(str1) // 2 + 1] if len(str1) % 2 == 1 else str1[:len(str1) // 2]
            half_str2 = str2[len(str2) // 2 + 1:] if len(str2) % 2 == 1 else str2[len(str2) // 2:]
            merged_string = half_str1 + half_str2
            shipPercent = random.randint(0, 100)
            shipBar = shipPercent // 10
            bar = [':red_square:' if i < shipBar else ':black_medium_square:' for i in range(10)]

            finalStr = f":heartpulse: **MATCHMAKING** :heartpulse:\n:small_red_triangle_down: `{str1}`\n:small_red_triangle: `{str2}`"
            embed = discord.Embed(
                color=discord.Color.pink(),
                title=f"**{merged_string}**",
                description=f"**{shipPercent}%** {''.join(bar)}{' PERFECT! ❤' if shipPercent == 100 else ''}",
            )
            embed.set_footer(text=f"*{self.shipNotes[shipBar]}*")
            return await ctx.reply(finalStr, embed=embed, mention_author=False)

async def setup(bot):
    await bot.add_cog(Fun(bot))
