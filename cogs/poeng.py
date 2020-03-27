# Discord Packages
import discord
from discord.ext import commands, tasks

# Bot Utilities
from cogs.utils.defaults import easy_embed

import asyncio
import codecs
import json
import os
import time


class Poeng(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.teller_data = {}
        self.cache_time = time.time()
        self.settings_file = bot.data_dir + '/poeng/innstilinger.json'
        self.teller_file = bot.data_dir + '/poeng/teller.json'
        self.load_json('settings')
        self.load_json('teller')
        self.bot.loop.create_task(self.cache_loop())


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.mentions:
            for word in self.settings_data['takk']:
                if word in message.content:
                    await self.add_star(message)

# TODO: halvstjerner?

    async def add_star(self, message, **kwarg):
        emoji = '⭐'
        dudes = {'id': [], 'mention': []}
        embed = easy_embed(self, message)
        for dude in message.mentions:
            if dude is self.bot.user:
                continue
            if dude is message.author:
                continue
            dudes['id'].append(dude.id)
            dudes["mention"].append(dude.mention)
        if not dudes['id']:
            return
        await message.add_reaction(emoji)
        msg_data = {
            'hjelper': dudes['id'],
            'giver': message.author.id,
            'link': message.jump_url
        }
        embed.title = "Ny stjerne tildelt!"
        embed.description = f'{message.author.mention} ga {",".join(dudes["mention"])} en stjerne!'



        def check(reaction, user):
            if user is None or user.id != message.author.id:
                return False

            if reaction.message.id != message.id:
                return False

            if reaction.emoji == emoji:
                return True
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)
            self.teller_data['meldinger'][str(message.id)] = msg_data
            self.cacher()
            await message.channel.send(embed=embed)
            await message.remove_reaction(emoji, self.bot.user)
            try:
                await message.remove_reaction(emoji, message.author)
            except:
                self.bot.logger.warn('Missing permission to remove reaction (manage_messages)')
        except asyncio.TimeoutError:
            await message.remove_reaction(emoji, self.bot.user)


    @commands.group(name="stjerne")
    async def pGroup(self, ctx):
        """Kategori for styring av poeng"""

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @pGroup.command(name="sjekk")
    async def check(self, ctx, user: discord.Member = None):
        if not user:
            user = ctx.author
        embed = easy_embed(self, ctx)
        counter = 0
        links = []
        for msg in self.teller_data['meldinger']:
            for helper in self.teller_data['meldinger'][msg]['hjelper']:
                if helper == user.id:
                    counter += 1
                    if counter <= 5:
                        embed.add_field(
                            name =f"Hjalp {self.bot.get_user(self.teller_data['meldinger'][msg]['giver']).name} her:",
                            value = f"[Link]({self.teller_data['meldinger'][msg]['link']})",
                            inline = False
                        )
        embed.title = "Boken"
        desc = f'{user.mention} har {counter} stjerner i boka.'
        if counter == 1:
            desc = f'{user.mention} har {counter} stjerne i boka'
        if 5 <= counter:
            desc = f'{user.mention} har {counter} stjerner i boka'
        if 10 <= counter:
            desc = f'{user.mention} har jobbet bra, her er det {counter} stjerner i boka!'
        if 15 <= counter:
            desc = f'{user.mention} har lagt inn en fantastisk jobb, {counter} stjerner i boka!'            
        if embed.fields:
            desc += f'\n\nViser de {len(embed.fields)} første:'
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.is_owner()
    @pGroup.group()
    async def admin(self, ctx):
        """Kategori for instillinger"""

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @admin.command(name='takk')
    async def set_thanks(self, ctx, thanks_phrase):
        try:
            self.settings_data['takk'].append(thanks_phrase)
            await ctx.send('La til {thanks_phrase} i lista')
        except KeyError:
            self.settings_data['takk'] = []
            self.settings_data['takk'].append(thanks_phrase)
        except:
            return self.bot.logger.error("Failed to set thanks_phrase: %s" % thanks_phrase)
        self.save_json('settings')
        self.load_json('settings')

    async def cache_loop(self):
        while True:
            self.cacher()
            await asyncio.sleep(30*60)

    def cacher(self):
        if time.time() - 120 > float(self.cache_time):
            self.save_json('teller')
            self.load_json('teller')
            self.bot.logger.debug('Reloaded data cache')
            self.cache_time = time.time()

    def load_json(self, mode):
        if mode == 'teller':
            with codecs.open(self.teller_file, 'r', encoding='utf8') as json_file:
                self.teller_data = json.load(json_file)
        elif mode == 'settings':
            with codecs.open(self.settings_file, 'r', encoding='utf8') as json_file:
                self.settings_data = json.load(json_file)


    def save_json(self, mode):
        if mode == 'teller':
            try:
                with codecs.open(self.teller_file, 'w', encoding='utf8') as outfile:
                    json.dump(self.teller_data, outfile, indent=4, sort_keys=True)
            except Exception as e:
                return self.bot.logger.warn('Failed to validate JSON before saving:\n%s\n%s' % (e,self.teller_data))
        elif mode == 'settings':
            try:
                with codecs.open(self.settings_file, 'w', encoding='utf8') as outfile:
                    json.dump(self.settings_data, outfile, indent=4, sort_keys=True)
            except Exception as e:
                return self.bot.logger.warn('Failed to validate JSON before saving:\n%s\n\n%s' % (e,self.settings_data))


def check_folder(data_dir):
    f = f'{data_dir}/poeng'
    if not os.path.exists(f):
        os.makedirs(f)


def check_files(data_dir):
    files = [
        {f'{data_dir}/poeng/teller.json': {'meldinger':{}}}, 
        {f'{data_dir}/poeng/innstilinger.json': {'takk':[]}}
        ]
    for i in files:
        for file, default in i.items():
            try:
                with codecs.open(file, 'r', encoding='utf8') as json_file:
                    json.load(json_file)
            except FileNotFoundError:
                with codecs.open(file, 'w', encoding='utf8') as outfile:
                    json.dump(default, outfile)


def setup(bot):
    check_folder(bot.data_dir)
    check_files(bot.data_dir)
    bot.add_cog(Poeng(bot))