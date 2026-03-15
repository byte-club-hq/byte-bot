import discord
from discord.ext import commands
import random

class InterviewView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=180)
        self.cog = cog # gives this View class access to the question bank in InterviewPrompt

    @discord.ui.button(label="Another Question", style=discord.ButtonStyle.primary)
    async def another_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = random.choice(self.cog.questions)

        embed = discord.Embed(
            title="More questions!",
            color=discord.Color.blue()
        )

        embed.add_field(name="Question:", value=q["question"], inline=False)
        embed.add_field(name="Answer", value=f"||{q['answer']}||", inline=False)
        embed.set_footer(text="😺Byte Club🤖")

        # updates the existing message with a different question instead of sending another reply
        await interaction.response.edit_message(embed=embed)

class InterviewPrompt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Sample(?) question bank
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
                "answer": "Use the math.floor() function"
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
        embed.set_footer(text="🤖Byte Club😸")

        view = InterviewView(self)

        view.add_item(
            discord.ui.Button(
                label="Quiz Source",
                style=discord.ButtonStyle.link,
                url="https://www.geeksforgeeks.org/python-interview-questions/"
            )
        )

        await ctx.reply(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(InterviewPrompt(bot))
