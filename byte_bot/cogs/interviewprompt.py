import discord
from discord.ext import commands
import random
from dataclasses import dataclass
import json

from byte_bot.cogs.utilities import logger

# Loads the question:answer from the json file
with open("byte_bot/data/interview_questions.json") as f:
    questions = json.load(f)

# Embed helper
def build_question_embed(q, title="Ready for an interview?"):
    embed = discord.Embed(title=title, color=discord.Color.blue())
    embed.add_field(name="Question:", value=q["question"], inline=False)
    embed.add_field(name="Answer", value=f"||{q['answer']}||", inline=False)
    embed.set_footer(text="🤖Byte Club😸")
    return embed

@dataclass
class InterviewView(discord.ui.View):
    questions: list
    previous_question: dict = None

    def __init__(self, cog):
        super().__init__(timeout=180)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        timeout_embed = discord.Embed(
            title="Timed Out",
            description="This session has expired. Send a new command to get another question!",
            color=discord.Color.dark_gray()
        )
        await self.message.edit(embed=timeout_embed, view=self)

    @discord.ui.button(label="Another Question", style=discord.ButtonStyle.primary)
    async def another_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        q = random.choice(questions)
        # Avoids sending the same question in a row
        while q == self.previous_question:
            q = random.choice(questions)
        self.previous_question = q

        embed = build_question_embed(q, title="More questions!")
        # Edits the embed with a new question instead of sending a new reply
        await interaction.response.edit_message(embed=embed)

@dataclass
class InterviewPrompt(commands.Cog):
    bot: commands.Bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.debug("InterviewPrompt cog is ready and loaded.")

    @commands.hybrid_command(description="Get a random Python interview question.")
    async def interviewprompt(self, ctx):
        """
            Sends a random Python interview question as a reply to '+interviewprompt' or '/interviewprompt'.

            The answer is hidden using a spoiler tag and can be revealed by clicking on it.
            A button is provided to fetch another question, which edits the existing embed in place.

            Returns:
                None: Sends an ephemeral embed directly to the user.
        """
        q = random.choice(questions)
        embed = build_question_embed(q)

        view = InterviewView(questions)

        view.add_item(
            discord.ui.Button(
                label="Quiz Source",
                style=discord.ButtonStyle.link,
                url="https://www.geeksforgeeks.org/python-interview-questions/"
            )
        )

        view.message = await ctx.reply(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(InterviewPrompt(bot))
