import discord
from discord.ext import commands
import requests
import re
import random
from dataclasses import dataclass
from typing import Literal
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

class LeetCode(commands.Cog):
    url = "https://leetcode.com/graphql"
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")

    @commands.hybrid_command()
    async def leetcode_profile(self, ctx, profile: str = None):

        if profile is None:
            await ctx.send("You must provide a leetcode username.\nUsage: `/leetcodeprofile <username>`\n", ephemeral=True)
            return

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
            self.url,
            json={"query": query, "variables": variables}
        )

        data = response.json()

        # First check if that users profile exists
        if not (user_data := data.get("data").get("matchedUser")):
            await ctx.send("Failed to find a leetcode user with that username", ephemeral=True)
            return

        # Parse the data
        profile_data = user_data.get("profile")
        submission_data = user_data.get("submitStats").get("acSubmissionNum")

        profile = Profile(
            real_name=profile_data.get("realName"),
            ranking=profile_data.get("ranking"),
            reputation=profile_data.get("reputation"),
            country=profile_data.get("countryName"),
        )

        submissions = [
            SubmissionStat(
                difficulty=stat.get("difficulty"),
                count=stat.get("count")
            )
            for stat in submission_data
        ]

        user = LeetCodeUser(
            username=user_data.get("username"),
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

    @commands.hybrid_command()
    async def leetcode_daily(self, ctx):
        query = """
                query questionOfToday {
                activeDailyCodingChallengeQuestion {
                    date
                    link
                    question {
                    title
                    titleSlug
                    difficulty
                    acRate
                    questionFrontendId
                    }
                }
                }
                """

        variables = {
        }
        response = requests.post(
            self.url,
            json={"query": query, "variables": variables}
        )

        data = response.json()

        # Parse the daily challenge json
        if not (problem_data := data.get("data", {}).get("activeDailyCodingChallengeQuestion")):
            await ctx.send("Failed to find a daily leetcode problem", ephemeral=True)
            return

        embed = discord.Embed()
        embed.add_field(name="Title", value=problem_data.get("question", {}).get("title"), inline=False)
        embed.add_field(name="Difficulty", value=problem_data.get("question", {}).get("difficulty"), inline=False)
        embed.add_field(name="Link", value="https://leetcode.com" + (problem_data.get("link")), inline=False)
        await ctx.send(embed=embed, ephemeral=True)


    @commands.hybrid_command()
    async def leetcode_random(self, ctx, difficulty: Literal["Easy", "Medium", "Hard"] | None = None):
        # Because filtering is no longer supported in the graphql endpoint I am querying the rest endpoint for all problems
        url = "https://leetcode.com/api/problems/all/"

        difficulties: dict[str, int] = {"Easy": 1, "Medium": 2, "Hard": 3}

        if difficulty not in difficulties:
            await ctx.send("You must provide a difficulty.\nUsage: `/leetcoderandom <difficulty>`\n", ephemeral=True)
            return

        response = requests.get(url)
        data = response.json()
        questions = data.get("stat_status_pairs")  # list of all problems

        # Filter by difficulty
        filtered = [
            q for q in questions
            if q.get("difficulty", {}).get("level") == difficulties.get(difficulty)
        ]
        
        random_problem = random.choice(filtered)

        embed = discord.Embed()
        embed.add_field(name="Title", value=random_problem.get("stat", {}).get("question__title"), inline=False)
        embed.add_field(name="Difficulty", value=f"{difficulty}", inline=False)
        embed.add_field(name="Link", value="https://leetcode.com/problems/" + (random_problem.get("stat", {}).get("question__title_slug")), inline=False)
        await ctx.send(embed=embed, ephemeral=True)



async def setup(bot):
    await bot.add_cog(LeetCode(bot))