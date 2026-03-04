import discord
from discord.ext import commands
import requests
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class SubmissionStat:
    difficulty: str
    count: int

@dataclass
class Profile:
    real_name: str
    ranking: int
    reputation: int
    country: str

@dataclass
class LeetCodeUser:
    username: str
    profile: Profile
    submissions: List[SubmissionStat]

class leetcode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")
    

    @commands.hybrid_command()
    async def leetcode(self, ctx, profile: str = None):

        if profile is None:
            await ctx.send("You must provide a leetcode username.\nUsage: `+leetcode <username>`")
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

        # Parse the data
        user_data = data["data"]["matchedUser"]

        profile_data = user_data["profile"]
        submission_data = user_data["submitStats"]["acSubmissionNum"]

        profile = Profile(
            real_name=profile_data["realName"],
            ranking=profile_data["ranking"],
            reputation=profile_data["reputation"],
            country=profile_data["countryName"],
        )

        submissions = [
            SubmissionStat(
                difficulty=stat["difficulty"],
                count=stat["count"]
            )
            for stat in submission_data
        ]

        user = LeetCodeUser(
            username=user_data["username"],
            profile=profile,
            submissions=submissions
        )
        
        # Create a discord Embed object to display
        embed = discord.Embed()
        embed.add_field(name="User", value=f"{user}")

        await ctx.send(embed=embed)

    
async def setup(bot):
    await bot.add_cog(leetcode(bot))