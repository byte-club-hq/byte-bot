import discord
from discord.ext import commands

class leetcode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")
    
    @commands.hybrid_command()
    async def leetcode(self, ctx):
        ### TODO add all the code to take in leetcode params and call a leetcode api
        await ctx.send("Hello from the leetcode function")
    
async def setup(bot):
    await bot.add_cog(leetcode(bot))