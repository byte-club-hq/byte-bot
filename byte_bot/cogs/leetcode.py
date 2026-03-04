import discord
from discord.ext import commands
import requests
import sys

class leetcode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")
    
    @commands.hybrid_command()
    async def leetcode(self, ctx, profile: str):

        if not profile:
            await ctx.send("Please enter the username of the leetcode profile you want to query. Ex: +leetcode <username>")
            return

        url = "https://leetcode.com/graphql"
        # This is where the graphql query happens, we can also query for problems, found this documentation https://jacoblincool.github.io/LeetCode-Query/
        query = """
                query getUserProfile($username: String!) {
                matchedUser(username: $username) {
                    username
                    profile {
                    realName
                    ranking
                    reputation
                    countryName
                    }
                    submitStats: submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                    }
                }
                }
                """
        variables = {
            "username": f"{profile}"
        }
        response = requests.post(
            url,
            json={"query": query, "variables": variables}
        )

        data = response.json()
        await ctx.send(data)

    
async def setup(bot):
    await bot.add_cog(leetcode(bot))