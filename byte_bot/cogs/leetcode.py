import discord
from discord.ext import commands
#import requests
import sys

class leetcode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")
    
    @commands.hybrid_command()
    async def leetcode(self, ctx):
        ### TODO add all the code to take in leetcode params and call a leetcode api
        print('sys exec =' + sys.executable)
        await ctx.send("Hello from the leetcode function")
        # url = "https://leetcode.com/graphql"
        # query = """
        #         query getUserProfile($username: String!) {
        #         matchedUser(username: $username) {
        #             username
        #             profile {
        #             realName
        #             ranking
        #             reputation
        #             countryName
        #             }
        #             submitStats: submitStatsGlobal {
        #             acSubmissionNum {
        #                 difficulty
        #                 count
        #             }
        #             }
        #         }
        #         }
        #         """
        # variables = {
        #     "username": "charleschang7"   # replace with target username
        # }
        # response = requests.post(
        #     url,
        #     json={"query": query, "variables": variables}
        # )

        # data = response.json()
        # print(data)

    
async def setup(bot):
    await bot.add_cog(leetcode(bot))