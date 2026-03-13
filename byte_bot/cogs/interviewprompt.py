import discord
from discord.ext import commands
import random

class InterviewPrompt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Sample question bank
        # Source: https://www.geeksforgeeks.org/python/python-interview-questions/
        self.questions = [
            {
                "question": "How can you concatenate two lists in Python?",
                "answer": "By using the + operator or the extend() method"
             },
            {
                "question": "What is the difference between for loop and while loop in Python",
                "answer": "For loops are used when we know how many times to repeat, often with lists, tuples, sets, or dictionaries. While loops are used when we only have an end condition and don’t know exactly how many times it will repeat."
            },
            {
                "question": "How do you floor a number in Python?",
                "answer": "To floor a number in Python, we can use the math.floor() function"
            },
            {
                "question": "What is the difference between / and // in Python?",
                "answer": "/ represents precise division (result is a floating point number) whereas // represents floor division (result is an integer)"
            },
            {
                "question": "Is Indentation Required in Python?",
                "answer": "Yes, indentation is required in Python"
            }
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        print('InterviewPrompt cog is ready!')

# Work in progress
    @commands.hybrid_command()
    async def interviewprompt(self, ctx):
        q = random.choice(self.questions)

        # Discord embed
        embed = discord.Embed(
            title="Ready for an interview?",
            description="Pop Python Quiz! (PPQ for short)",
            color=discord.Color.blue()
        )
        embed.add_field(name="Question:", value=q["question"], inline=False)
        embed.add_field(name="Answer", value=f"||{q['answer']}||", inline=False)
        embed.add_field(name="Quiz Source:", value="[link](https://www.geeksforgeeks.org/python/python-interview-questions/)", inline=False)
        embed.set_footer(text="🤖Byte Club😸")

        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(InterviewPrompt(bot))
