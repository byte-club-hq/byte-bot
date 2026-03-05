import discord
from discord.ext import commands

class InterviewPrompt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('InterviewPrompt cog is ready!')

    @commands.hybrid_command()
    async def interviewprompt(self, ctx):

        # discord Embed
        embed = discord.Embed(title="embed test", description="embed testing", color=discord.Color.blue())
        embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/1.png")
        embed.add_field(name="Interview prompt", value="test question")
        embed.set_footer(text="Byte Club")

        await ctx.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(InterviewPrompt(bot))
