import discord
from discord.ext import commands
import requests
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class SubmissionStat:
    difficulty: str | None
    count: int | None

@dataclass
class Profile:
    real_name: str | None
    ranking: int | None
    reputation: int | None
    country: str | None

@dataclass
class LeetCodeUser:
    username: str | None
    profile: Profile | None
    submissions: List[SubmissionStat] | None

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

        # First check if that users profile exists
        if not (user_data := data["data"].get("matchedUser")):
            await ctx.send("Failed to find a leetcode user with that username", ephemeral=True)
            return

        # Parse the data
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

        embed.add_field(name="User", value=user.username, inline=False)

        embed.add_field(name="Profile", value=user.profile.real_name, inline=False)
        embed.add_field(name="Ranking", value=user.profile.ranking, inline=True)
        embed.add_field(name="Reputation", value=user.profile.reputation, inline=True)

        embed.add_field(name="Submissions", value="Total Problems solved 🎉", inline=False)

        for stat in submissions:
            embed.add_field(name=f"{stat.difficulty}", value=f"{stat.count}", inline=True)

        await ctx.send(embed=embed, ephemeral=True)

    
async def setup(bot):
    await bot.add_cog(leetcode(bot))