import discord
from discord.ext import commands

from byte_bot.services.leetcode_service import get_leetcode_profile, get_leetcode_daily, get_leetcode_random

class LeetCode(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bytebot is online")

    @commands.hybrid_command()
    async def leetcode_profile(self, ctx, profile: str | None = None):

        if profile is None:
            await ctx.send("You must provide a leetcode username.\nUsage: `/leetcodeprofile <username>`\n", ephemeral=True)
            return

        try:
            user = get_leetcode_profile(profile)
        except ValueError as err:
            await ctx.send(str(err), ephemeral=True)
            return
        
        # Create a discord Embed object to display
        embed = discord.Embed()
        embed.add_field(name="User", value=user.username, inline=False)
        embed.add_field(name="Profile", value=user.profile.real_name, inline=False)
        embed.add_field(name="Ranking", value=user.profile.ranking, inline=True)
        embed.add_field(name="Reputation", value=user.profile.reputation, inline=True)
        embed.add_field(name="Submissions", value="Total Problems solved 🎉", inline=False)

        for stat in user.submissions:
            embed.add_field(name=f"{stat.difficulty}", value=f"{stat.count}", inline=True)

        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command()
    async def leetcode_daily(self, ctx):

        try:
            problem_data = get_leetcode_daily()
        except ValueError as err:
            await ctx.send(str(err), ephemeral=True)
            return

        embed = discord.Embed()
        embed.add_field(name="Title", value=problem_data.get("question", {}).get("title"), inline=False)
        embed.add_field(name="Difficulty", value=problem_data.get("question", {}).get("difficulty"), inline=False)
        embed.add_field(name="Link", value="https://leetcode.com" + (problem_data.get("link")), inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command()
    async def leetcode_random(self, ctx, difficulty = None):
        
        try:
            random_problem = get_leetcode_random(difficulty)
        except ValueError as err:
            await ctx.send(str(err), ephemeral=True)
            return

        embed = discord.Embed()
        embed.add_field(name="Title", value=random_problem.get("stat", {}).get("question__title"), inline=False)
        embed.add_field(name="Difficulty", value=f"{difficulty}", inline=False)
        embed.add_field(name="Link", value="https://leetcode.com/problems/" + (random_problem.get("stat", {}).get("question__title_slug")), inline=False)
        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LeetCode(bot))
