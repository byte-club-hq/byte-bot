import discord
from discord.ext import commands
import random

class InterviewPrompt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Sample question bank
        # Source: https://www.geeksforgeeks.org/python/python-interview-questions/
        # Naive approach??
        self.questions = [
            "Is Python a compiled language or an interpreted language?",
            "How can you concatenate two lists in Python?",
            "Difference between for loop and while loop in Python",
            "How do you floor a number in Python?",
            "What is the difference between / and // in Python?"
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        print('InterviewPrompt cog is ready!')

# Work in progress
    @commands.hybrid_command()
    async def interviewprompt(self, ctx):
        question = random.choice(self.questions)

        # Discord embed
        embed = discord.Embed(title="Ready for an interview?", description="Try answering these Python questions!", color=discord.Color.blue())
        embed.add_field(name="Question:", value=question, inline=False)
        # Also naive, you'd have to scroll through the page to find the answer
        embed.add_field(name="Answer:", value="[Check answer](https://www.geeksforgeeks.org/python/python-interview-questions/)", inline=False)
        embed.set_footer(text="🤖Byte Club😸")

        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(InterviewPrompt(bot))
