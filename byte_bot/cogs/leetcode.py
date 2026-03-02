import discord
from discord.ext import commands

class leetcode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")
    
    @commands.command()
    async def leetcode(self, ctx):
        await ctx.send("Hello")
    
async def setup(bot):
    await bot.add_cog(leetcode(bot))